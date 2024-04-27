from typing import NamedTuple


class TableInfo(NamedTuple):
    """A named tuple to represent a table row in the IoT pages"""
    name: str
    value: str = None
    action_url: str = None
    action_name: str = 'configure'
    """text shown on the <a> tag button"""
    action_target: str = None
    """target of the action <a> tag. Generally '_blank' for opening a new tab"""
    name_icon: str = None
    """font awesome icon class to show before the name"""
    action_iot_documentation_url: str = None
    """URL to the IoT documentation for the action.
    Will be used instead of `action_url` if provided."""
    iot_documentation_url: str = None
    is_warning: bool = False
    """If True, the row will be highlighted as a warning"""
