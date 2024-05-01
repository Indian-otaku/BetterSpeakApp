import os

class Config:
    SAVED_W2V2_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_model", "w2v2_architecture")
    SAVED_CHECKPOINT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_model")

