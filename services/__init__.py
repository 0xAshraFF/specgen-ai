"""SpecGen AI — Services Package"""
from .video_processor import extract_keyframes, get_video_info, VideoProcessingError
from .ai_client import generate_spec, SpecGenerationError
