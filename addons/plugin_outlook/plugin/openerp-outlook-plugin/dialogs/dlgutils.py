# Generic utilities for dialog functions.

# This module is part of the spambayes project, which is Copyright 2003
# The Python Software Foundation and is covered by the Python Software
# Foundation license.

def MAKELONG(l,h):
    return ((h & 0xFFFF) << 16) | (l & 0xFFFF)

MAKELPARAM=MAKELONG

def SetWaitCursor(wait):
    import win32gui, win32con
    if wait:
        hCursor = win32gui.LoadCursor(0, win32con.IDC_WAIT)
    else:
        hCursor = win32gui.LoadCursor(0, 0)
    win32gui.SetCursor(hCursor)
