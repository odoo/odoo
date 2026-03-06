from typing import List, Optional


DEFAULT_IGNORE_LIST = [
    'nose.plugins',
    'six.moves',
    'django.utils.six.moves',
    'google.gax',
    'threading',
    'Queue',
    'selenium',
    '_pytest.terminal.',
    '_pytest.runner.',
    'gi',
]


class Settings:
    def __init__(self, default_ignore_list: Optional[List[str]]=None) -> None:
        self.default_ignore_list = default_ignore_list or DEFAULT_IGNORE_LIST[:]


settings = Settings()


class ConfigurationError(Exception):
    pass


def configure(default_ignore_list: Optional[List[str]]=None, extend_ignore_list: Optional[List[str]]=None) -> None:
    if default_ignore_list is not None and extend_ignore_list is not None:
        raise ConfigurationError("Either default_ignore_list or extend_ignore_list might be given, not both")
    if default_ignore_list:
        settings.default_ignore_list = default_ignore_list
    if extend_ignore_list:
        settings.default_ignore_list = [*settings.default_ignore_list, *extend_ignore_list]


def reset_config() -> None:
    global settings
    settings = Settings()
