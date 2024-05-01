import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoModelForAudioClassification
import numpy as np
from config import Config

def get_batched_data(recorded_audio, sample_rate=16000, chunk_duration_seconds=3):
    waveform = np.frombuffer(b''.join(recorded_audio), dtype=np.float32)
    waveform = torch.from_numpy(np.copy(waveform))
    chunk_size = int(sample_rate * chunk_duration_seconds)
    chunks = torch.split(waveform, chunk_size, dim=0)
    chunks = list(chunks)
    if chunks[len(chunks)-1].shape[-1] != chunk_size:
        chunks[len(chunks)-1] = _pad_if_necessary(chunks[len(chunks)-1], chunk_size)
    return torch.stack(chunks)

def _pad_if_necessary(signal, num_samples):
    if signal.shape[0] < num_samples:
        pad_len = num_samples - signal.shape[0]
        signal = torch.nn.functional.pad(signal, (0, pad_len))
    return signal
    
class Wav2Vec2Model(nn.Module):
    def __init__(
            self,
            config=Config
    ):
        super(Wav2Vec2Model, self).__init__()
        self.config = config

        if os.path.exists(Config.SAVED_W2V2_PATH):
            self.model = AutoModelForAudioClassification.from_pretrained(Config.SAVED_W2V2_PATH)
        else:
            self.model = AutoModelForAudioClassification.from_pretrained("facebook/wav2vec2-base", num_labels=1)
            self.model.save_pretrained(Config.SAVED_W2V2_PATH)

        for param in self.model.parameters():
            param.requires_grad = False

    def forward(self, input_data):
        out = self.model(input_data).logits
        return out
    
def get_pretrained_model(saved_checkpoint_path):
    model = Wav2Vec2Model(Config).to("cpu")
    model.load_state_dict(torch.load(saved_checkpoint_path, map_location=torch.device("cpu"))["state_dict"])
    model.eval()
    return model


def get_result(recorded_audio, model_type="prolongation"):

    if model_type == "prolongation":
        MODEL_FILE = "prolongation.pth"
    elif model_type == "interjection":
        MODEL_FILE = "interjection.ckpt"
    elif model_type == "repetition":
        MODEL_FILE = "repetition.pth"


    batched_data = get_batched_data(recorded_audio)
    model = get_pretrained_model(os.path.join(Config.SAVED_CHECKPOINT_PATH, MODEL_FILE))
    logits = model(batched_data)
    probs = torch.sigmoid(logits).squeeze()
    prediction = torch.round(probs)
    confidence = torch.where((prediction == 1), probs, 1 - probs)
    return prediction, confidence
