import os
import sys

import pythoncom
import win32api
import winerror
from win32com.axdebug import adb, axdebug, documents, gateways
from win32com.axdebug.codecontainer import SourceCodeContainer
from win32com.axdebug.util import _wrap
from win32com.server.exception import COMException

debuggingTrace = "DEBUG_AXDEBUG" in os.environ  # Should we print "trace" output?


def trace(*args):
    """A function used instead of "print" for debugging output."""
    if not debuggingTrace:
        return
    print(win32api.GetCurrentThreadId(), end=" ")
    for arg in args:
        print(arg, end=" ")
    print()


# Note that the DebugManager is not a COM gateway class for the
# debugger - but it does create and manage them.
class DebugManager:
    _debugger_interfaces_ = [axdebug.IID_IActiveScriptDebug]

    def __init__(self, scriptEngine):
        self.scriptEngine = scriptEngine
        self.adb = adb.Debugger()
        self.rootNode = None
        self.debugApplication = None
        self.ccProvider = documents.CodeContainerProvider()
        try:
            self.scriptSiteDebug = scriptEngine.GetScriptSite(
                axdebug.IID_IActiveScriptSiteDebug
            )
        except pythoncom.com_error:
            # No debugger interface (ie, dumb host).  Do the extra work.
            trace("Scripting site has no debugger interface")
            self.scriptSiteDebug = None
        # Get the debug application object.
        self.debugApplication = None
        if self.scriptSiteDebug is not None:
            # Spec says that we should test for this, and if it fails revert to
            # PDM application.
            try:
                self.debugApplication = self.scriptSiteDebug.GetApplication()
                self.rootNode = self.scriptSiteDebug.GetRootApplicationNode()
            except pythoncom.com_error:
                self.debugApplication = None

        if self.debugApplication is None:
            # Try to get/create the default one
            # NOTE - Don't catch exceptions here - let the parent do it,
            # so it knows debug support is available.
            pdm = pythoncom.CoCreateInstance(
                axdebug.CLSID_ProcessDebugManager,
                None,
                pythoncom.CLSCTX_ALL,
                axdebug.IID_IProcessDebugManager,
            )
            self.debugApplication = pdm.GetDefaultApplication()
            self.rootNode = self.debugApplication.GetRootNode()

        assert self.debugApplication is not None, (
            "Need to have a DebugApplication object by now!"
        )
        self.activeScriptDebug = None

        if self.debugApplication is not None:
            self.adb.AttachApp(self.debugApplication, self.ccProvider)
        self.codeContainers = {}
        self.activeScriptDebug = _wrap(
            ActiveScriptDebug(self, self.codeContainers), axdebug.IID_IActiveScriptDebug
        )

    def Close(self):
        # Called by the language engine when it receives a close request
        self.activeScriptDebug = None
        self.scriptEngine = None
        self.rootNode = None
        self.debugApplication = None
        self.scriptSiteDebug = None
        if self.ccProvider is not None:
            self.ccProvider.Close()
            self.ccProvider = None
        self.codeContainers = {}
        if self.adb:
            self.adb.CloseApp()
            self.adb = None

    # print("Close complete")

    def IsAnyHost(self):
        "Do we have _any_ debugging interfaces installed?"
        return self.debugApplication is not None

    def IsSimpleHost(self):
        return self.scriptSiteDebug is None

    def HandleRuntimeError(self):
        """Called by the engine when a runtime error occurs.  If we have a debugger,
        we let it know.

        The result is a boolean which indicates if the error handler should call
        IActiveScriptSite::OnScriptError()
        """
        # 		if self.IsAnyHost:
        # 			site = _wrap(self, axdebug.IID_IActiveScriptSite)
        # 			breakResume, errorResume, fCallOnError = self.debugApplication(activeScriptErrorDebug, site)
        # Do something with these!
        # 		else:
        trace("HandleRuntimeError")
        fCallOnError = 1
        return fCallOnError

    def _query_interface_for_debugger_(self, iid):
        if iid in self._debugger_interfaces_:
            return self.activeScriptDebug
        trace("DebugManager QI - unknown IID", iid)
        return 0

    def OnEnterScript(self):
        trace("OnEnterScript")
        self.adb.SetupAXDebugging(sys._getframe().f_back)

    def OnLeaveScript(self):
        trace("OnLeaveScript")
        self.adb.ResetAXDebugging()

    def AddScriptBlock(self, codeBlock):
        # If we don't have debugging support, don't bother.
        cc = DebugCodeBlockContainer(codeBlock, self.scriptSiteDebug)
        if self.IsSimpleHost():
            document = documents.DebugDocumentText(cc)
            document = _wrap(document, axdebug.IID_IDebugDocument)
            provider = documents.DebugDocumentProvider(document)
            provider = _wrap(provider, axdebug.IID_IDebugDocumentProvider)
            cc.debugDocument = document
            newNode = self.debugApplication.CreateApplicationNode()
            newNode.SetDocumentProvider(provider)
            newNode.Attach(self.rootNode)
        else:
            newNode = None  # Managed by smart host.
            self.codeContainers[cc.sourceContext] = cc
        self.ccProvider.AddCodeContainer(cc, newNode)


class DebugCodeBlockContainer(SourceCodeContainer):
    def __init__(self, codeBlock, site):
        self.codeBlock = codeBlock
        SourceCodeContainer.__init__(
            self,
            codeBlock.codeText,
            codeBlock.GetFileName(),
            codeBlock.sourceContextCookie,
            codeBlock.startLineNumber,
            site,
        )

    def GetName(self, dnt):
        if dnt == axdebug.DOCUMENTNAMETYPE_APPNODE:
            return self.codeBlock.GetDisplayName()
        elif dnt == axdebug.DOCUMENTNAMETYPE_TITLE:
            return self.codeBlock.GetDisplayName()
        # 		elif dnt==axdebug.DOCUMENTNAMETYPE_FILE_TAIL:
        # 		elif dnt==axdebug.DOCUMENTNAMETYPE_URL:
        else:
            raise COMException(scode=winerror.S_FALSE)


class EnumDebugCodeContexts(gateways.EnumDebugCodeContexts):
    def _wrap(self, ob):
        return ob


class ActiveScriptDebug:
    """The class which implements the IActiveScriptDebug interface for the Active Script engine.

    Only ever used by smart hosts.
    """

    _public_methods_ = [
        "GetScriptTextAttributes",
        "GetScriptletTextAttributes",
        "EnumCodeContextsOfPosition",
    ]
    _com_interfaces_ = [axdebug.IID_IActiveScriptDebug]

    def __init__(self, debugMgr, codeContainers):
        self.debugMgr = debugMgr
        self.scriptSiteDebug = debugMgr.scriptSiteDebug
        self.codeContainers = codeContainers

    def _Close(self):
        self.debugMgr = None
        self.scriptSiteDebug = None
        self.codeContainers = {}

    def _query_interface_(self, iid):
        trace("DebuggerQI with", iid)
        return _wrap(self.debugMgr.scriptEngine, iid)

    def GetScriptTextAttributes(self, code, delim, flags):
        container = SourceCodeContainer(code, "<Temp Code Block>")
        return container.GetSyntaxColorAttributes()

    def GetScriptletTextAttributes(self, code, delim, flags):
        trace("GetScriptletTextAttributes", code, delim, flags)
        container = SourceCodeContainer(code, "<Temp Code Block>")
        return container.GetSyntaxColorAttributes()

    def EnumCodeContextsOfPosition(self, context, charOffset, numChars):
        trace("EnumCodeContextsOfPosition", context, charOffset, numChars)
        try:
            context = self.codeContainers[context].GetCodeContextAtPosition(charOffset)
        except KeyError:
            raise COMException(scode=winerror.E_UNEXPECTED)
        enum = EnumDebugCodeContexts([context])
        return _wrap(enum, axdebug.IID_IEnumDebugCodeContexts)
