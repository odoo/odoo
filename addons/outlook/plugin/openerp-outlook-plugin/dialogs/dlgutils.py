# Generic utilities for dialog functions.

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
