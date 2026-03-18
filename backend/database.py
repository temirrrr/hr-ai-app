from functools import lru_cache

from services import HRCommandCenter


@lru_cache(maxsize=1)
def get_service() -> HRCommandCenter:
    return HRCommandCenter()
