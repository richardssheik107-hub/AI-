import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    VOLC_AK = os.getenv("VOLC_ACCESS_KEY")
    VOLC_SK = os.getenv("VOLC_SECRET_KEY")
    ARK_ENDPOINT_ID = os.getenv("ARK_ENDPOINT_ID")
    ARK_API_KEY = os.getenv("ARK_API_KEY")
    ARK_MAX_TOKENS = int(os.getenv("ARK_MAX_TOKENS", "120"))
    ARK_SERVICE_TIER = os.getenv("ARK_SERVICE_TIER", "fast")
    ARK_REASONING_EFFORT = os.getenv("ARK_REASONING_EFFORT", "minimal")

    RTC_APP_ID = os.getenv("RTC_APP_ID")
    RTC_APP_KEY = os.getenv("RTC_APP_KEY")
    RTC_TOKEN = os.getenv("RTC_TOKEN")
    RTC_ROOM_ID = os.getenv("RTC_ROOM_ID", "ChatRoom01")
    RTC_USER_ID = os.getenv("RTC_USER_ID", "Huoshan01")

    AIGC_TASK_ID = os.getenv("AIGC_TASK_ID", "ChatTask01")
    AIGC_AGENT_USER_ID = os.getenv("AIGC_AGENT_USER_ID", "ChatBot01")
    AIGC_WELCOME_MESSAGE = os.getenv("AIGC_WELCOME_MESSAGE", "你好，我是小宁，有什么需要帮忙的吗？")

    ASR_APP_ID = os.getenv("ASR_APP_ID")
    ASR_CLUSTER = os.getenv("ASR_CLUSTER", "volcengine_streaming_common")
    TTS_APP_ID = os.getenv("TTS_APP_ID")
    TTS_CLUSTER = os.getenv("TTS_CLUSTER", "volcano_tts")
    TTS_VOICE_TYPE = os.getenv("TTS_VOICE_TYPE", "BV001_streaming")
    
    SERVER_URL = os.getenv("SERVER_URL")

    VOLC_ACCOUNT_ID = os.getenv("VOLC_ACCOUNT_ID")
    KB_PROJECT_NAME = os.getenv("KB_PROJECT_NAME", "default")
    KB_COLLECTION_NAME = os.getenv("KB_COLLECTION_NAME", "dw_ai")
    KB_SEARCH_LIMIT = int(os.getenv("KB_SEARCH_LIMIT", "1"))
    KB_MAX_CONTEXT_CHARS = int(os.getenv("KB_MAX_CONTEXT_CHARS", "3000"))
    KB_REQUEST_TIMEOUT = float(os.getenv("KB_REQUEST_TIMEOUT", "10"))
    KB_CACHE_TTL_SECONDS = int(os.getenv("KB_CACHE_TTL_SECONDS", "300"))
    KB_CACHE_MAX_SIZE = int(os.getenv("KB_CACHE_MAX_SIZE", "128"))
    KB_RERANK_ENABLED = os.getenv("KB_RERANK_ENABLED", "true").lower() in ("1", "true", "yes", "on")
    KB_RERANK_CANDIDATES = int(os.getenv("KB_RERANK_CANDIDATES", "3"))
    KB_RERANK_TOP_N = int(os.getenv("KB_RERANK_TOP_N", str(KB_SEARCH_LIMIT)))

settings = Config()
