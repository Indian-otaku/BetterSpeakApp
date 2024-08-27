# BetterSpeak Desktop App
BetterSpeak is a powerful desktop application designed to assist individuals in improving their speech fluency. This PyQt5-based application provides real-time analysis and feedback to help users track and enhance their speech clarity.

# Key Features
* Speech Fluency Analysis: Detects speech disfluencies, providing feedback for better clarity and fluency.
* Waveform Visualization: Displays speech waveforms to help users visualize their speech patterns and intensity.
* Graphs and Data: Offers visualization options with waveforms.
* User-Friendly Interface: Intuitive and modern design with a focus on usability.
  
# Installation
To run the BetterSpeak app, you must convert the PyQt5 code into an executable using PyInstaller. Here are the steps:

1. Install PyInstaller via pip:
`pip install -r requirements.txt`.
2. Navigate to the directory containing your BetterSpeak code and run:
`pyi-makespec main.py --noconsole --splash .\betterspeaklogo.ico --icon .\betterspeaklogo.ico` followed by `pyinstaller main.spec`.
4. Run the generated executable file. 
