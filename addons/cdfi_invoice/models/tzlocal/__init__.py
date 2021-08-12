import sys
if sys.platform == 'win32':
    from .win32 import get_localzone, reload_localzone
else:
    from .unix import get_localzone, reload_localzone
    
