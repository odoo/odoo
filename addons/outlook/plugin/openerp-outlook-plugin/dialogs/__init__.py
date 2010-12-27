# This package defines dialog boxes used by the main

# This module is part of the spambayes project, which is Copyright 2003
# The Python Software Foundation and is covered by the Python Software
# Foundation license.
import os, sys, stat
#import dialog_map

def LoadDialogs(rc_name = "dialogs.rc"):
    base_name = os.path.splitext(rc_name)[0]
    mod_name = "dialogs.resources." + base_name
    mod = None
    # If we are running from source code, check the .py file is up to date
    # wrt the .rc file passed in.
    # If we are running from binaries, the rc name is not used at all - we
    # assume someone running from source previously generated the .py!
    if not hasattr(sys, "frozen"):
        from resources import rc2py
        rc_path = os.path.dirname( rc2py.__file__ )
        if not os.path.isabs(rc_name):
            rc_name = os.path.join( rc_path, rc_name)
        py_name = os.path.join(rc_path, base_name + ".py")
        mtime = size = None
        if os.path.exists(py_name):
            try:
                mod = __import__(mod_name)
                mod = sys.modules[mod_name]
                mtime = mod._rc_mtime_
                size = mod._rc_size_
            except (ImportError, AttributeError):
                mtime = None
        try:
            stat_data = os.stat(rc_name)
            rc_mtime = stat_data[stat.ST_MTIME]
            rc_size = stat_data[stat.ST_SIZE]
        except OSError:
            rc_mtime = rc_size = None
        if rc_mtime!=mtime or rc_size!=size:
            # Need to generate the dialog.
            print "Generating %s from %s" % (py_name, rc_name)
            rc2py.convert(rc_name, py_name)
            if mod is not None:
                reload(mod)
    if mod is None:
        mod = __import__(mod_name)
        mod = sys.modules[mod_name]
    return mod.FakeParser()

def ShowDialog(parent, manager, config, idd):
    """Displays another dialog"""
    if manager.dialog_parser is None:
        manager.dialog_parser = LoadDialogs()
    import dialog_map
    print dir(dialog_map)
    commands = dialog_map.dialog_map[idd]
    if not parent:
        import win32gui
        try:
            parent = win32gui.GetActiveWindow()
        except win32gui.error:
            pass

    import dlgcore
    dlg = dlgcore.ProcessorDialog(parent, manager, config, idd, commands)
    return dlg.DoModal()

def MakePropertyPage(parent, manager, config, idd, yoffset=24):
    """Creates a child dialog box to use as property page in a tab control"""
    if manager.dialog_parser is None:
        manager.dialog_parser = LoadDialogs()
    import dialog_map
    commands = dialog_map.dialog_map[idd]
    if not parent:
        raise "Parent must be the tab control"

    import dlgcore
    dlg = dlgcore.ProcessorPage(parent, manager, config, idd, commands, yoffset)
    return dlg

import dlgutils
SetWaitCursor = dlgutils.SetWaitCursor
