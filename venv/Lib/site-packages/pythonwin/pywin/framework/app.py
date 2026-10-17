# Application stuff.
# The application is responsible for managing the main frame window.
#
# We also grab the FileOpen command, to invoke our Python editor
"The PythonWin application code. Manages most aspects of MDI, etc"

from __future__ import annotations

import builtins
import os
import sys
import traceback
import warnings
from typing import TYPE_CHECKING

import regutil
import win32api
import win32con
import win32ui
from pywin.mfc import afxres, dialog, window
from pywin.mfc.thread import WinApp

from . import scriptutils

if TYPE_CHECKING:
    from typing_extensions import Literal


# Helper for writing a Window position by name, and later loading it.
def SaveWindowSize(section, rect, state=""):
    """Writes a rectangle to an INI file
    Args: section = section name in the applications INI file
          rect = a rectangle in a (cy, cx, y, x) tuple
                 (same format as CREATESTRUCT position tuples)."""
    left, top, right, bottom = rect
    if state:
        state += " "
    win32ui.WriteProfileVal(section, state + "left", left)
    win32ui.WriteProfileVal(section, state + "top", top)
    win32ui.WriteProfileVal(section, state + "right", right)
    win32ui.WriteProfileVal(section, state + "bottom", bottom)


def LoadWindowSize(section, state=""):
    """Loads a section from an INI file, and returns a rect in a tuple (see SaveWindowSize)"""
    if state:
        state += " "
    left = win32ui.GetProfileVal(section, state + "left", 0)
    top = win32ui.GetProfileVal(section, state + "top", 0)
    right = win32ui.GetProfileVal(section, state + "right", 0)
    bottom = win32ui.GetProfileVal(section, state + "bottom", 0)
    return (left, top, right, bottom)


def RectToCreateStructRect(rect):
    return (rect[3] - rect[1], rect[2] - rect[0], rect[1], rect[0])


# Define FrameWindow and Application objects
#
# The Main Frame of the application.
class MainFrame(window.MDIFrameWnd):
    sectionPos = "Main Window"
    statusBarIndicators = (
        afxres.ID_SEPARATOR,  # // status line indicator
        afxres.ID_INDICATOR_CAPS,
        afxres.ID_INDICATOR_NUM,
        afxres.ID_INDICATOR_SCRL,
        win32ui.ID_INDICATOR_LINENUM,
        win32ui.ID_INDICATOR_COLNUM,
    )

    def OnCreate(self, cs) -> Literal[-1, 0, 1]:
        self._CreateStatusBar()
        return 0

    def _CreateStatusBar(self):
        self.statusBar = win32ui.CreateStatusBar(self)
        self.statusBar.SetIndicators(self.statusBarIndicators)
        self.HookCommandUpdate(self.OnUpdatePosIndicator, win32ui.ID_INDICATOR_LINENUM)
        self.HookCommandUpdate(self.OnUpdatePosIndicator, win32ui.ID_INDICATOR_COLNUM)

    def OnUpdatePosIndicator(self, cmdui):
        editControl = scriptutils.GetActiveEditControl()
        value = " " * 5
        if editControl is not None:
            try:
                startChar, endChar = editControl.GetSel()
                lineNo = editControl.LineFromChar(startChar)
                colNo = endChar - editControl.LineIndex(lineNo)

                if cmdui.m_nID == win32ui.ID_INDICATOR_LINENUM:
                    value = "%0*d" % (5, lineNo + 1)
                else:
                    value = "%0*d" % (3, colNo + 1)
            except win32ui.error:
                pass
        cmdui.SetText(value)
        cmdui.Enable()

    def PreCreateWindow(self, cc):
        cc = self._obj_.PreCreateWindow(cc)
        pos = LoadWindowSize(self.sectionPos)
        self.startRect = pos
        if pos[2] - pos[0]:
            rect = RectToCreateStructRect(pos)
            cc = cc[0], cc[1], cc[2], cc[3], rect, cc[5], cc[6], cc[7], cc[8]
        return cc

    def OnDestroy(self, msg):
        # use GetWindowPlacement(), as it works even when min'd or max'd
        rectNow = self.GetWindowPlacement()[4]
        if rectNow != self.startRect:
            SaveWindowSize(self.sectionPos, rectNow)
        return 0


class CApp(WinApp):
    "A class for the application"

    def __init__(self):
        self.oldCallbackCaller = None
        WinApp.__init__(self, win32ui.GetApp())
        self.idleHandlers = []

    def InitInstance(self):
        "Called to crank up the app"
        HookInput()
        numMRU = win32ui.GetProfileVal("Settings", "Recent File List Size", 10)
        win32ui.LoadStdProfileSettings(numMRU)
        # self._obj_.InitMDIInstance()

        # install a "callback caller" - a manager for the callbacks
        # self.oldCallbackCaller = win32ui.InstallCallbackCaller(self.CallbackManager)
        self.LoadMainFrame()
        self.SetApplicationPaths()

    def ExitInstance(self):
        "Called as the app dies - too late to prevent it here!"
        win32ui.OutputDebug("Application shutdown\n")
        # Restore the callback manager, if any.
        try:
            win32ui.InstallCallbackCaller(self.oldCallbackCaller)
        except AttributeError:
            pass
        if self.oldCallbackCaller:
            del self.oldCallbackCaller
        self.frame = None  # clean Python references to the now destroyed window object.
        self.idleHandlers = []
        # Attempt cleanup if not already done!
        if self._obj_:
            self._obj_.AttachObject(None)
        self._obj_ = None
        return 0

    def HaveIdleHandler(self, handler):
        return handler in self.idleHandlers

    def AddIdleHandler(self, handler):
        self.idleHandlers.append(handler)

    def DeleteIdleHandler(self, handler):
        self.idleHandlers.remove(handler)

    def OnIdle(self, count):
        try:
            ret = 0
            handlers = self.idleHandlers[:]  # copy list, as may be modified during loop
            for handler in handlers:
                try:
                    thisRet = handler(handler, count)
                except:
                    print(f"Idle handler {handler!r} failed")
                    traceback.print_exc()
                    print("Idle handler removed from list")
                    try:
                        self.DeleteIdleHandler(handler)
                    except ValueError:  # Item not in list.
                        pass
                    thisRet = 0
                ret = ret or thisRet
            return ret
        except KeyboardInterrupt:
            pass

    def CreateMainFrame(self):
        return MainFrame()

    def LoadMainFrame(self):
        "Create the main applications frame"
        self.frame = self.CreateMainFrame()
        self.SetMainFrame(self.frame)
        self.frame.LoadFrame(win32ui.IDR_MAINFRAME, win32con.WS_OVERLAPPEDWINDOW)
        self.frame.DragAcceptFiles()  # we can accept these.
        self.frame.ShowWindow(win32ui.GetInitialStateRequest())
        self.frame.UpdateWindow()
        self.HookCommands()

    def OnHelp(self, id, code):
        try:
            if id == win32ui.ID_HELP_GUI_REF:
                helpFile = regutil.GetRegisteredHelpFile("Pythonwin Reference")
                helpCmd = win32con.HELP_CONTENTS
            else:
                helpFile = regutil.GetRegisteredHelpFile("Main Python Documentation")
                helpCmd = win32con.HELP_FINDER
            if helpFile is None:
                win32ui.MessageBox("The help file is not registered!")
            else:
                from . import help

                help.OpenHelpFile(helpFile, helpCmd)
        except:
            t, v, tb = sys.exc_info()
            win32ui.MessageBox(f"Internal error in help file processing\r\n{t}: {v}")
            tb = None  # Prevent a cycle

    def DoLoadModules(self, modules):
        # XXX - this should go, but the debugger uses it :-(
        # don't do much checking!
        for module in modules:
            __import__(module)

    def HookCommands(self):
        self.frame.HookMessage(self.OnDropFiles, win32con.WM_DROPFILES)
        self.HookCommand(self.HandleOnFileOpen, win32ui.ID_FILE_OPEN)
        self.HookCommand(self.HandleOnFileNew, win32ui.ID_FILE_NEW)
        self.HookCommand(self.OnFileMRU, win32ui.ID_FILE_MRU_FILE1)
        self.HookCommand(self.OnHelpAbout, win32ui.ID_APP_ABOUT)
        self.HookCommand(self.OnHelp, win32ui.ID_HELP_PYTHON)
        self.HookCommand(self.OnHelp, win32ui.ID_HELP_GUI_REF)
        # Hook for the right-click menu.
        self.frame.GetWindow(win32con.GW_CHILD).HookMessage(
            self.OnRClick, win32con.WM_RBUTTONDOWN
        )

    def SetApplicationPaths(self):
        # Load the users/application paths
        new_path = []
        apppath = win32ui.GetProfileVal("Python", "Application Path", "").split(";")
        for path in apppath:
            if len(path) > 0:
                new_path.append(win32ui.FullPath(path))
        for extra_num in range(1, 11):
            apppath = win32ui.GetProfileVal(
                "Python", "Application Path %d" % extra_num, ""
            ).split(";")
            if len(apppath) == 0:
                break
            for path in apppath:
                if len(path) > 0:
                    new_path.append(win32ui.FullPath(path))
        sys.path = new_path + sys.path

    def OnRClick(self, params):
        "Handle right click message"
        # put up the entire FILE menu!
        menu = win32ui.LoadMenu(win32ui.IDR_TEXTTYPE).GetSubMenu(0)
        menu.TrackPopupMenu(params[5])  # track at mouse position.
        return 0

    def OnDropFiles(self, msg):
        "Handle a file being dropped from file manager"
        hDropInfo = msg[2]
        self.frame.SetActiveWindow()  # active us
        nFiles = win32api.DragQueryFile(hDropInfo)
        try:
            for iFile in range(0, nFiles):
                fileName = win32api.DragQueryFile(hDropInfo, iFile)
                win32ui.GetApp().OpenDocumentFile(fileName)
        finally:
            win32api.DragFinish(hDropInfo)

        return 0

    # No longer used by Pythonwin, as the C++ code has this same basic functionality
    # but handles errors slightly better.
    # It all still works, tho, so if you need similar functionality, you can use it.
    # Therefore I haven't deleted this code completely!
    # 	def CallbackManager( self, ob, args = () ):
    # 		"""Manage win32 callbacks.  Trap exceptions, report on them, then return 'All OK'
    # 		to the frame-work. """
    # 		import traceback
    # 		try:
    # 			ret = apply(ob, args)
    # 			return ret
    # 		except:
    # 			# take copies of the exception values, else other (handled) exceptions may get
    # 			# copied over by the other fns called.
    # 			win32ui.SetStatusText('An exception occurred in a windows command handler.')
    # 			t, v, tb = sys.exc_info()
    # 			traceback.print_exception(t, v, tb.tb_next)
    # 			try:
    # 				sys.stdout.flush()
    # 			except (NameError, AttributeError):
    # 				pass

    # Command handlers.
    def OnFileMRU(self, id, code):
        "Called when a File 1-n message is received"
        fileName = win32ui.GetRecentFileList()[id - win32ui.ID_FILE_MRU_FILE1]
        win32ui.GetApp().OpenDocumentFile(fileName)

    def HandleOnFileOpen(self, id, code):
        "Called when FileOpen message is received"
        win32ui.GetApp().OnFileOpen()

    def HandleOnFileNew(self, id, code):
        "Called when FileNew message is received"
        win32ui.GetApp().OnFileNew()

    def OnHelpAbout(self, id, code):
        "Called when HelpAbout message is received.  Displays the About dialog."
        win32ui.InitRichEdit()
        dlg = AboutBox()
        dlg.DoModal()


def _GetRegistryValue(key, val, default=None):
    # val is registry value - None for default val.
    try:
        hkey = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, key)
        return win32api.RegQueryValueEx(hkey, val)[0]
    except win32api.error:
        try:
            hkey = win32api.RegOpenKey(win32con.HKEY_LOCAL_MACHINE, key)
            return win32api.RegQueryValueEx(hkey, val)[0]
        except win32api.error:
            return default


scintilla = "Scintilla is Copyright 1998-2020 Neil Hodgson (https://www.scintilla.org)"
idle = "This program uses IDLE extensions by Guido van Rossum, Tim Peters and others."
contributors = "Thanks to the following people for making significant contributions: Roger Upole, Sidnei da Silva, Sam Rushing, Curt Hagenlocher, Dave Brennan, Roger Burnham, Gordon McMillan, Neil Hodgson, Laramie Leavitt. (let me know if I have forgotten you!)"


# The About Box
class AboutBox(dialog.Dialog):
    def __init__(self, idd=win32ui.IDD_ABOUTBOX):
        dialog.Dialog.__init__(self, idd)

    def OnInitDialog(self):
        text = "Pythonwin - Python IDE and GUI Framework for Windows.\n\n{}\n\nPython is {}\n\n{}\n\n{}\n\n{}".format(
            win32ui.copyright, sys.copyright, scintilla, idle, contributors
        )
        self.SetDlgItemText(win32ui.IDC_EDIT1, text)
        import sysconfig

        site_packages = sysconfig.get_paths()["platlib"]
        version_path = os.path.join(site_packages, "pywin32.version.txt")
        try:
            with open(version_path) as f:
                ver = "pywin32 build %s" % f.read().strip()
        except OSError:
            ver = None
        if not ver:
            warnings.warn(
                f"Could not read pywin32's version from '{version_path}'", stacklevel=1
            )
        self.SetDlgItemText(win32ui.IDC_ABOUT_VERSION, ver)
        self.HookCommand(self.OnButHomePage, win32ui.IDC_BUTTON1)

    def OnButHomePage(self, id, code):
        if code == win32con.BN_CLICKED:
            win32api.ShellExecute(
                0, "open", "https://github.com/mhammond/pywin32", None, "", 1
            )


def Win32Input(prompt=None):
    "Provide input() for gui apps"
    # flush stderr/out first.
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except:
        pass
    if prompt is None:
        prompt = ""
    ret = dialog.GetSimpleInput(prompt)
    if ret is None:
        raise KeyboardInterrupt("operation cancelled")
    return ret


def HookInput():
    builtins.input = Win32Input


def HaveGoodGUI():
    """Returns true if we currently have a good gui available."""
    return "pywin.framework.startup" in sys.modules


def CreateDefaultGUI(appClass=None):
    """Creates a default GUI environment"""
    if appClass is None:
        from . import intpyapp  # Bring in the default app - could be param'd later.

        appClass = intpyapp.InteractivePythonApp
    # Create and init the app.
    appClass().InitInstance()


def CheckCreateDefaultGUI():
    """Checks and creates if necessary a default GUI environment."""
    rc = HaveGoodGUI()
    if not rc:
        CreateDefaultGUI()
    return rc
