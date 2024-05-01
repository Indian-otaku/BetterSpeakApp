from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QHBoxLayout, QVBoxLayout,  QPushButton, QLabel, QStackedWidget, QTextEdit, QListWidget
from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal, QMutex, QWaitCondition
from PyQt5.QtGui import QPixmap
import pyqtgraph as pg
import sys
import os
import pyaudio
import wave
from datetime import datetime
import numpy as np
import torch

import matplotlib
matplotlib.use('Qt5Agg')
from syllable_counter import find_syllable_count_from_sentences
from get_model_result import get_result


DURATION = 5  # In seconds
CHUNK_SIZE = 1024
SAMPLE_RATE = 16000
SINGLE_SECOND_N_FRAMES = int(SAMPLE_RATE / CHUNK_SIZE)
N_FRAMES = int(SINGLE_SECOND_N_FRAMES * DURATION)


##################################################################################################
##################################################################################################
##################################################################################################

class RecordingAudioThread(QThread):
    frames_ready = pyqtSignal(bytes)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.is_running = False
        self.audio = None
        self.stream = None

    def run(self):
        self.is_running = True
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paFloat32, 
            channels=1, 
            rate=SAMPLE_RATE, 
            input=True, 
            frames_per_buffer=CHUNK_SIZE
        )

        while self.is_running:
            data = self.stream.read(CHUNK_SIZE)
            self.frames_ready.emit(data) 
        
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()
        self.audio = None
        self.stream = None
    
    def stop(self):
        self.is_running = False

class PlayingAudioThread(QThread):
    def __init__(self, parent=None, bytes_audio=b"") -> None:
        super().__init__(parent)
        self.audio = None
        self.stream = None
        self.bytes_audio = bytes_audio

    def run(self):
        self.is_running = True
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        )

        try:
            self.stream.write(self.bytes_audio)
        except Exception as e:
            print(f"Error during audio playback: {e}")
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.audio.terminate()
            self.audio = None
            self.stream = None

class SavingAudioThread(QThread):
    def __init__(self, parent=None, bytes_audio=b"", save_dir="") -> None:
        super().__init__(parent)
        self.bytes_audio = bytes_audio
        self.save_dir = save_dir

    def run(self):
        if not os.path.exists(self.save_dir):
            os.mkdir(save_path)
        save_path = os.path.join(self.save_dir, datetime.now().strftime("%H-%M_%d-%m-%Y") + ".wav")
        audio_data = (np.frombuffer(self.bytes_audio, dtype=np.float32) * 32767).astype(np.int16)
        with wave.open(save_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data)
        print("File saved on path: ", save_path)

class RunModelThread(QThread):
    resultReady = pyqtSignal(int)

    def __init__(self, parent=None, bytes_audio=[], model_type="prolongation") -> None:
        super().__init__(parent)
        self.model_type = model_type
        self.bytes_audio = bytes_audio
        self.mutex = QMutex()
        self.condition = QWaitCondition()

    def run(self):
        pred, conf = get_result(self.bytes_audio, model_type=self.model_type)
        self.result = int(torch.sum(pred).item())
        self.resultReady.emit(self.result)


class StutterCountThread(QThread):
    aggregatedResultReady = pyqtSignal(int)

    def __init__(self, modelThreads):
        super().__init__()
        self.modelThreads = modelThreads

    def run(self):
        aggregatedResult = 0
        for modelThread in self.modelThreads:
            modelThread.start()
            modelThread.wait()
            aggregatedResult += modelThread.result
            
        self.aggregatedResultReady.emit(aggregatedResult)



##################################################################################################
##################################################################################################
##################################################################################################


class BetterSpeakApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BetterSpeak")

        self.threads = {}
        self.mutex = QMutex()
        self.saved_recordings_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_recordings")

        self.central_widget = QWidget()
        self.central_widget.setObjectName("central_widget")
        self.setCentralWidget(self.central_widget)
        self.master_layout = QHBoxLayout(self.central_widget)

        self.options = QWidget()
        self.options_layout = QVBoxLayout(self.options)

        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "betterspeaklogo.jpg")
        self.options_logo = QLabel("Better speak")
        self.options_logo.setPixmap(QPixmap(logo_path).scaledToWidth(250))
        self.options_layout.addWidget(self.options_logo, alignment=Qt.AlignHCenter | Qt.AlignTop)

        self.page1_button = QPushButton("PSS Calculation", self)
        self.page1_button.setObjectName("page1_button")
        self.page1_button.clicked.connect(self.show_page1)
        self.options_layout.addWidget(self.page1_button)

        self.page2_button = QPushButton("Random", self)
        self.page2_button.setObjectName("page2_button")
        self.page2_button.clicked.connect(self.show_page2)
        self.options_layout.addWidget(self.page2_button)

        self.master_layout.addWidget(self.options, stretch=15)

        self.stacked_widgets = QStackedWidget()
        self.stacked_widgets.setObjectName("stacked_widgets")
        self.master_layout.addWidget(self.stacked_widgets, stretch=85)
        self.create_page1()

        self.showMaximized()



    def create_page1(self):
        
        # Design part 

        self.page1 = QWidget()
        self.page1.setObjectName("page1")
        self.page1_layout = QVBoxLayout(self.page1)

        self.page1_row1 = QLabel("Calculate %SS")
        self.page1_row1.setObjectName("page1_row1")
        self.page1_layout.addWidget(self.page1_row1, stretch=10)

        self.page1_row2 = QLabel("Read the text while recording the audio")
        self.page1_row2.setObjectName("page1_row2")
        self.page1_layout.addWidget(self.page1_row2, stretch=5)

        self.page1_row3 = QHBoxLayout()
        self.page1_row3_text_part = QTextEdit("Enter your text here...")
        self.page1_row3_text_part.setObjectName("page1_row3_text_part")
        self.page1_row3_right_part = QWidget()
        self.page1_row3_right_part.setObjectName("page1_row3_right_part")
        self.page1_row3_right_part_layout = QVBoxLayout(self.page1_row3_right_part)
        self.page1_row3_result_part = QLabel("This is where we are supposed to show results")
        self.page1_row3_result_part.setObjectName("page1_row3_result_part")
        self.page1_row3_right_part_layout.addWidget(self.page1_row3_result_part)


        self.page1_row3.addWidget(self.page1_row3_text_part, stretch=80)
        self.page1_row3.addWidget(self.page1_row3_right_part, stretch=20)
        self.page1_layout.addLayout(self.page1_row3, stretch=55)

        self.page1_row4 = QWidget()
        self.page1_row4.setObjectName("page1_row4")     
        self.page1_row4_layout = QHBoxLayout(self.page1_row4)

        self.page1_row4_wavegraph = pg.PlotWidget()
        self.page1_row4_wavegraph.setObjectName("page1_row4_wavegraph")
        self.page1_row4_wavegraph.setBackground("w") # White graph for now. Change it later when we include dark mode.
        self.page1_row4_wavegraph.setTitle("Waveform", color="gray", size="10pt")
        self.page1_row4_wavegraph.setLabel("left", "Intensity")
        self.page1_row4_wavegraph.setLabel("bottom", "Time")
        self.page1_row4_wavegraph.showGrid(x=True, y=True)
        self.page1_row4_wavegraph.setYRange(-1.1, 1.1)
        self.page1_row4_wavegraph.hideAxis('bottom')
        self.pen = pg.mkPen(color=(255, 0, 0))

        self.main_buttons()
        self.graph_buttons()



        self.page1_row4_layout.addWidget(self.page1_row4_wavegraph, stretch=80)
        self.page1_row4_layout.addWidget(self.page1_row4_buttons, stretch=20)
        self.page1_layout.addWidget(self.page1_row4, stretch=30)


        self.stacked_widgets.addWidget(self.page1)


        # Events

        self.page1_row3_start_button.clicked.connect(self.start_recording)
        self.page1_row3_pause_button.clicked.connect(self.pause_recording)
        self.page1_row3_pss_button.clicked.connect(self.pss_calculation)
        self.page1_row3_play_button.clicked.connect(self.play_recording)
        self.page1_row3_save_button.clicked.connect(self.save_recording)


    def main_buttons(self):
        self.page1_row3_buttons = QWidget()
        self.page1_row3_buttons.setObjectName("page1_row3_buttons")
        self.page1_row3_buttons_layout = QVBoxLayout(self.page1_row3_buttons)
        self.page1_row3_start_button = QPushButton("Start recording", )
        self.page1_row3_start_button.setObjectName("page1_row3_start_button")
        self.page1_row3_pause_button = QPushButton("Pause recording", )
        self.page1_row3_pause_button.setObjectName("page1_row3_pause_button")
        self.page1_row3_pss_button = QPushButton("Calculate metrics")
        self.page1_row3_pss_button.setObjectName("page1_row3_pss_button")
        self.page1_row3_play_button = QPushButton("Play recording")
        self.page1_row3_play_button.setObjectName("page1_row3_play_button")
        self.page1_row3_save_button = QPushButton("Save recording")
        self.page1_row3_save_button.setObjectName("page1_row3_save_button")
        self.record_audio()
        self.page1_row3_buttons_layout.addWidget(self.page1_row3_start_button, alignment=Qt.AlignCenter)
        self.page1_row3_buttons_layout.addWidget(self.page1_row3_pause_button, alignment=Qt.AlignCenter)
        self.page1_row3_buttons_layout.addWidget(self.page1_row3_pss_button, alignment=Qt.AlignCenter)
        self.page1_row3_buttons_layout.addWidget(self.page1_row3_play_button, alignment=Qt.AlignCenter)
        self.page1_row3_buttons_layout.addWidget(self.page1_row3_save_button, alignment=Qt.AlignCenter)
        self.page1_row3_right_part_layout.addWidget(self.page1_row3_buttons)


        self.page1_row3_start_button.setFixedWidth(200)
        self.page1_row3_pause_button.setFixedWidth(200)
        self.page1_row3_pss_button.setFixedWidth(200)
        self.page1_row3_play_button.setFixedWidth(200)
        self.page1_row3_save_button.setFixedWidth(200)

        self.page1_row3_start_button.setCursor(Qt.PointingHandCursor)
        self.page1_row3_pause_button.setCursor(Qt.PointingHandCursor)
        self.page1_row3_pss_button.setCursor(Qt.PointingHandCursor)
        self.page1_row3_play_button.setCursor(Qt.PointingHandCursor)
        self.page1_row3_save_button.setCursor(Qt.PointingHandCursor)


    def graph_buttons(self):
        self.page1_row4_buttons = QWidget()
        self.page1_row4_buttons.setObjectName("page1_row4_buttons")
        self.page1_row4_buttons_layout = QVBoxLayout(self.page1_row4_buttons)
        self.page1_row4_graph_button_part = QPushButton("This is where the buttons for the graph is supposed to be")
        self.page1_row4_buttons_layout.addWidget(self.page1_row4_graph_button_part)


    def record_audio(self):
        self.recorded_audio = []
        self.recording_thread = RecordingAudioThread()
        self.recording_thread.frames_ready.connect(self.process_frames)

        self.waveform = self.page1_row4_wavegraph.plot(
            [], [], pen=self.pen
        )


    def start_recording(self):
        if not self.recording_thread.isRunning():
            self.recording_thread.start()

        self.syllable_count = find_syllable_count_from_sentences(self.page1_row3_text_part.toPlainText())
        self.page1_row3_result_part.setText(f"Syllable count: {self.syllable_count}\n")

    def pause_recording(self):
        if self.recording_thread.isRunning():
            self.recording_thread.stop()
        else:
            self.recording_thread.start()

    def pss_calculation(self):  
        if self.recording_thread.isRunning():
            self.recording_thread.stop()

        modelThreads = [
            RunModelThread(bytes_audio=self.recorded_audio, model_type="interjection"),
            RunModelThread(bytes_audio=self.recorded_audio, model_type="prolongation"),
            RunModelThread(bytes_audio=self.recorded_audio, model_type="repetition")
        ]
        modelThreads[0].resultReady.connect(self.update_interjection_count)
        modelThreads[1].resultReady.connect(self.update_prolongation_count)
        modelThreads[2].resultReady.connect(self.update_repetition_count)
        self.stutter_count_thread = StutterCountThread(modelThreads=modelThreads)
        self.stutter_count_thread.aggregatedResultReady.connect(self.update_stutter_count)
        self.stutter_count_thread.start()

    def update_interjection_count(self, count):
        existing_text = self.page1_row3_result_part.text()
        self.page1_row3_result_part.setText(existing_text + f"Interjection count: {count}\n")

    def update_prolongation_count(self, count):
        existing_text = self.page1_row3_result_part.text()
        self.page1_row3_result_part.setText(existing_text + f"Prolongation count: {count}\n")
    
    def update_repetition_count(self, count):
        existing_text = self.page1_row3_result_part.text()
        self.page1_row3_result_part.setText(existing_text + f"Repetition count: {count}\n")

    def update_stutter_count(self, count):
        existing_text = self.page1_row3_result_part.text()
        self.page1_row3_result_part.setText(existing_text + f"Total stutter count: {count}\n")
        self.page1_row3_result_part.setText(existing_text + f"PSS : {(float(count) / self.syllable_count)*100.0} %\n")
        
    def play_recording(self):
        if getattr(self, 'playing_thread', None) and self.playing_thread.isRunning():
            return
    
        self.playing_thread = PlayingAudioThread(bytes_audio=b''.join(self.recorded_audio))
        self.playing_thread.start()

    def save_recording(self):
        if self.recording_thread.isRunning():
            self.recording_thread.stop()
        self.saving_thread = SavingAudioThread(
            bytes_audio=b''.join(self.recorded_audio), 
            save_dir=self.saved_recordings_directory
            )
        self.saving_thread.start()

    def process_frames(self, frames: bytes):
        self.mutex.lock()
        try:
            self.recorded_audio.append(frames)
            intensities = np.frombuffer(b''.join(self.recorded_audio[-N_FRAMES:]), dtype=np.float32)
            time = np.linspace(0, DURATION, len(intensities))
            self.waveform.setData(time, intensities)
        finally:
            self.mutex.unlock()
        

    def show_page1(self):
        self.create_page1()
        self.stacked_widgets.setCurrentWidget(self.page1)

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #

    def create_page2(self):
        
        # Design part 

        self.page2 = QWidget()
        self.page2.setObjectName("page2")
        self.page2_layout = QVBoxLayout(self.page2)

        self.page2_layout.addWidget(QLabel("'Damn this is great application' - the creator himself"))


        self.stacked_widgets.addWidget(self.page2)

    def show_page2(self):
        self.create_page2()
        self.stacked_widgets.setCurrentWidget(self.page2)

# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> #






if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = BetterSpeakApp()
    css_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles.css")
    with open(css_filepath, "r") as f:
        css_code = f.read()
    main_window.setStyleSheet(css_code)
    main_window.show()
    sys.exit(app.exec_())
