# This module is part of the spambayes project, which is Copyright 2003
# The Python Software Foundation and is covered by the Python Software
# Foundation license.

# Package that manages and defines dialog resources

def GetImageParamsFromBitmapID(rc_parser, bmpid):
    import os, sys
    import win32gui, win32con, win32api
    if type(bmpid)==type(0):
        bmpid = rc_parser.names[bmpid]
    int_bmpid = rc_parser.ids[bmpid]
    # For both binary and source versions, we currently load from files.
    # In future py2exe built binary versions we will be able to load the
    # bitmaps directly from our DLL.
    filename = rc_parser.bitmaps[bmpid]
    if hasattr(sys, "frozen"):
        # in our .exe/.dll - load from that.
        if sys.frozen=="dll":
            hmod = sys.frozendllhandle
        else:
            hmod = win32api.GetModuleHandle(None)
        return hmod, int_bmpid, 0
    else:
        # source code - load the .bmp directly.
        if not os.path.isabs(filename):
            # In this directory
            filename = os.path.join( os.path.dirname( __file__ ), filename)
        return 0, filename, win32con.LR_LOADFROMFILE
    assert 0, "not reached"
