__name__="package"

import uno
import unohelper
import os
#--------------------------------------------------
# An ActionListener adapter.
# This object implements com.sun.star.awt.XActionListener.
# When actionPerformed is called, this will call an arbitrary
#  python procedure, passing it...
#   1. the oActionEvent
#   2. any other parameters you specified to this object's constructor (as a tuple).
if __name__<>"package":
    os.system( "ooffice '-accept=socket,host=localhost,port=2002;urp;'" )
passwd=""
database=""
uid=""
loginstatus=False
from com.sun.star.awt import XActionListener
class ActionListenerProcAdapter( unohelper.Base, XActionListener ):
    def __init__( self, oProcToCall, tParams=() ):
        self.oProcToCall = oProcToCall # a python procedure
        self.tParams = tParams # a tuple

    # oActionEvent is a com.sun.star.awt.ActionEvent struct.
    def actionPerformed( self, oActionEvent ):
        if callable( self.oProcToCall ):
            apply( self.oProcToCall, (oActionEvent,) + self.tParams )

#--------------------------------------------------
# An ItemListener adapter.
# This object implements com.sun.star.awt.XItemListener.
# When itemStateChanged is called, this will call an arbitrary
#  python procedure, passing it...
#   1. the oItemEvent
#   2. any other parameters you specified to this object's constructor (as a tuple).
from com.sun.star.awt import XItemListener
class ItemListenerProcAdapter( unohelper.Base, XItemListener ):
    def __init__( self, oProcToCall, tParams=() ):
        self.oProcToCall = oProcToCall # a python procedure
        self.tParams = tParams # a tuple

    # oItemEvent is a com.sun.star.awt.ItemEvent struct.
    def itemStateChanged( self, oItemEvent ):
        if callable( self.oProcToCall ):
            apply( self.oProcToCall, (oItemEvent,) + self.tParams )

#--------------------------------------------------
# An TextListener adapter.
# This object implements com.sun.star.awt.XTextistener.
# When textChanged is called, this will call an arbitrary
#  python procedure, passing it...
#   1. the oTextEvent
#   2. any other parameters you specified to this object's constructor (as a tuple).
from com.sun.star.awt import XTextListener
class TextListenerProcAdapter( unohelper.Base, XTextListener ):
    def __init__( self, oProcToCall, tParams=() ):
        self.oProcToCall = oProcToCall # a python procedure
        self.tParams = tParams # a tuple

    # oTextEvent is a com.sun.star.awt.TextEvent struct.
    def textChanged( self, oTextEvent ):
        if callable( self.oProcToCall ):
            apply( self.oProcToCall, (oTextEvent,) + self.tParams )


if __name__<>"package":
    from gui import *
class ErrorDialog:
    def __init__(self,sErrorMsg, sErrorHelpMsg="",sTitle="Error Message"):
        self.win = DBModalDialog(50, 50, 150, 90, sTitle)
        self.win.addFixedText("lblErrMsg", 5, 5, 190, 25, sErrorMsg)
        self.win.addFixedText("lblErrHelpMsg", 5, 30, 190, 25, sErrorHelpMsg)
        self.win.addButton('btnOK', 55,-5,40,15,'Ok'
                     ,actionListenerProc = self.btnOkOrCancel_clicked )
        self.win.doModalDialog("",None)
    def btnOkOrCancel_clicked( self, oActionEvent ):
        self.win.endExecute()

import uno
import xmlrpclib
import re
import socket
import cPickle
import marshal
import tempfile
if __name__<>"package":
    from gui import *
    from logreport import *
    from rpc import *
    database="test"
    uid = 1

def genTree(object,aList,insField,host,level=3, ending=[], ending_excl=[], recur=[], root='', actualroot=""):
    try:
        global url
        sock=RPCSession(url)
        global passwd
        res = sock.execute(database, uid, passwd, object , 'fields_get')
        key = res.keys()
        key.sort()
        for k in key:
            if (not ending or res[k]['type'] in ending) and ((not ending_excl) or not (res[k]['type'] in ending_excl)):
                insField.addItem(root+'/'+res[k]["string"],len(aList))
                aList.append(actualroot+'/'+k)
            if (res[k]['type'] in recur) and (level>0):
                genTree(res[k]['relation'],aList,insField,host ,level-1, ending, ending_excl, recur,root+'/'+res[k]["string"],actualroot+'/'+k)
    except:
        obj=Logger()
        import traceback,sys
        info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
        obj.log_write('Function', LOG_ERROR, info)

def VariableScope(oTcur,insVariable,aObjectList,aComponentAdd,aItemList,sTableName=""):
    if sTableName.find(".") != -1:
	for i in range(len(aItemList)):
            if aComponentAdd[i]==sTableName:
		sLVal=aItemList[i][1][aItemList[i][1].find(",'")+2:aItemList[i][1].find("')")]
                for j in range(len(aObjectList)):
		    if aObjectList[j][:aObjectList[j].find("(")] == sLVal:
                        insVariable.append(aObjectList[j])
	VariableScope(oTcur,insVariable,aObjectList,aComponentAdd,aItemList, sTableName[:sTableName.rfind(".")])
    else:
	for i in range(len(aItemList)):
            if aComponentAdd[i]==sTableName:
		sLVal=aItemList[i][1][aItemList[i][1].find(",'")+2:aItemList[i][1].find("')")]
                for j in range(len(aObjectList)):
		    if aObjectList[j][:aObjectList[j].find("(")] == sLVal and sLVal!="":
                        insVariable.append(aObjectList[j])

def getList(aObjectList,host,count):
    desktop=getDesktop()
    doc =desktop.getCurrentComponent()
    docinfo=doc.getDocumentInfo()
    sMain=""
    if not count == 0:
        if count >= 1:
            oParEnum = doc.getTextFields().createEnumeration()
            while oParEnum.hasMoreElements():
                oPar = oParEnum.nextElement()
                if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
                    sItem=oPar.Items[1]
                    if sItem[sItem.find("(")+1:sItem.find(",")]=="objects":
                        sMain = sItem[sItem.find(",'")+2:sItem.find("')")]
                        oParEnum = doc.getTextFields().createEnumeration()
                        while oParEnum.hasMoreElements():
                            oPar = oParEnum.nextElement()
                            if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
                                sItem=oPar.Items[1]
                                if sItem[sItem.find("[[ ")+3:sItem.find("(")]=="repeatIn":
                                    if sItem[sItem.find("(")+1:sItem.find(",")]=="objects":
                                        aObjectList.append(sItem[sItem.rfind(",'")+2:sItem.rfind("')")] + "(" + docinfo.getUserFieldValue(3) + ")")
                                    else:
                                        sTemp=sItem[sItem.find("(")+1:sItem.find(",")]
                                        if sMain == sTemp[:sTemp.find(".")]:
                                            getRelation(docinfo.getUserFieldValue(3), sItem[sItem.find(".")+1:sItem.find(",")], sItem[sItem.find(",'")+2:sItem.find("')")],aObjectList,host)
                                        else:
                                            sPath=getPath(sItem[sItem.find("(")+1:sItem.find(",")], sMain)
                                            getRelation(docinfo.getUserFieldValue(3), sPath, sItem[sItem.find(",'")+2:sItem.find("')")],aObjectList,host)
    else:
        aObjectList.append("List of " + docinfo.getUserFieldValue(3))

def getRelation(sRelName, sItem, sObjName, aObjectList, host ):
        global url
        sock=RPCSession(url)
        global passwd
        res = sock.execute(database, uid, passwd, sRelName , 'fields_get')
        key = res.keys()
        for k in key:
            if sItem.find(".") == -1:
                if k == sItem:
                    aObjectList.append(sObjName + "(" + res[k]['relation'] + ")")
                    return 0
	    if k == sItem[:sItem.find(".")]:
		getRelation(res[k]['relation'], sItem[sItem.find(".")+1:], sObjName,aObjectList,host)


def getPath(sPath,sMain):
    desktop=getDesktop()
    doc =desktop.getCurrentComponent()
    oParEnum = doc.getTextFields().createEnumeration()
    while oParEnum.hasMoreElements():
        oPar = oParEnum.nextElement()
        if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
            sItem=oPar.Items[1]
	    if sPath[:sPath.find(".")] == sMain:
                break;
            else:
                res = re.findall('\\[\\[ *([a-zA-Z0-9_\.]+) *\\]\\]',sPath)
                if len(res) <> 0:
		    if sItem[sItem.find(",'")+2:sItem.find("')")] == sPath[:sPath.find(".")]:
			sPath =  sItem[sItem.find("(")+1:sItem.find(",")] + sPath[sPath.find("."):]
                        getPath(sPath, sMain)
    return sPath

def EnumDocument(aItemList,aComponentAdd):
    desktop = getDesktop()
    parent=""
    bFlag = False
    Doc =desktop.getCurrentComponent()
    #oVC = Doc.CurrentController.getViewCursor()
    oParEnum = Doc.getTextFields().createEnumeration()
    while oParEnum.hasMoreElements():
        oPar = oParEnum.nextElement()
        if oPar.Anchor.TextTable:
            #parent = oPar.Anchor.TextTable.Name
            getChildTable(oPar.Anchor.TextTable,aItemList,aComponentAdd)
        elif oPar.Anchor.TextSection:
            parent = oPar.Anchor.TextSection.Name
        elif oPar.Anchor.Text:
            parent = "Document"
        sItem=oPar.Items[1].replace(' ',"")
        if sItem[sItem.find("[[ ")+3:sItem.find("(")]=="repeatIn" and not oPar.Items in aItemList:
            templist=oPar.Items[0],sItem
            aItemList.append( templist )
        aComponentAdd.append( parent )

def getChildTable(oPar,aItemList,aComponentAdd,sTableName=""):
    sNames = oPar.getCellNames()
    bEmptyTableFlag=True
    for val in sNames:
        oCell = oPar.getCellByName(val)
        oCurEnum = oCell.createEnumeration()
        while oCurEnum.hasMoreElements():
            try:
                oCur = oCurEnum.nextElement()

                if oCur.supportsService("com.sun.star.text.TextTable"):
                    if sTableName=="":
                        getChildTable(oCur,aItemList,aComponentAdd,oPar.Name)
                    else:
                        getChildTable(oCur,aItemList,aComponentAdd,sTableName+"."+oPar.Name)
                else:
                    oSecEnum = oCur.createEnumeration()
                    while oSecEnum.hasMoreElements():
                        oSubSection = oSecEnum.nextElement()
                        if oSubSection.supportsService("com.sun.star.text.TextField"):
                            bEmptyTableFlag=False
                            sItem=oSubSection.TextField.Items[1]
                            if sItem[sItem.find("[[ ")+3:sItem.find("(")]=="repeatIn":
                                if aItemList.__contains__(oSubSection.TextField.Items)==False:
                                    aItemList.append(oSubSection.TextField.Items)
                                if sTableName=="":
                                    if  aComponentAdd.__contains__(oPar.Name)==False:
                                        aComponentAdd.append(oPar.Name)
                                else:
                                    if aComponentAdd.__contains__(sTableName+"."+oPar.Name)==False:
                                        aComponentAdd.append(sTableName+"."+oPar.Name)
            except:
                obj=Logger()
                import traceback,sys
                info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                obj.log_write('Function', LOG_ERROR, info)
    if bEmptyTableFlag==True:
        aItemList.append((u'',u''))
        if sTableName=="":
            if  aComponentAdd.__contains__(oPar.Name)==False:
                aComponentAdd.append(oPar.Name)
        else:
            if aComponentAdd.__contains__(sTableName+"."+oPar.Name)==False:
                aComponentAdd.append(sTableName+"."+oPar.Name)
    return 0

def getRecersiveSection(oCurrentSection,aSectionList):
        desktop=getDesktop()
        doc =desktop.getCurrentComponent()
        oParEnum=doc.getText().createEnumeration()
        aSectionList.append(oCurrentSection.Name)
        if oCurrentSection.ParentSection:
            getRecersiveSection(oCurrentSection.ParentSection,aSectionList)
        else:
            return

def GetAFileName():
    oFileDialog=None
    iAccept=None
    sPath=""
    InitPath=""
    oUcb=None
    oFileDialog = createUnoService("com.sun.star.ui.dialogs.FilePicker")
    oUcb = createUnoService("com.sun.star.ucb.SimpleFileAccess")
    oFileDialog.appendFilter("OpenERP Report File","*.sxw")
    oFileDialog.setCurrentFilter("OpenERP Report File")
    if InitPath == "":
        InitPath =tempfile.gettempdir()
    #End If
    if oUcb.exists(InitPath):
        oFileDialog.setDisplayDirectory(InitPath)
    #End If
    iAccept = oFileDialog.execute()
    if iAccept == 1:
        sPath = oFileDialog.Files[0]
    oFileDialog.dispose()
    return sPath


import uno
import unohelper
import pythonloader
if __name__<>"package":
    from actions import *


#------------------------------------------------------------
#   Uno ServiceManager access
#   A different version of this routine and global variable
#    is needed for code running inside a component.
#------------------------------------------------------------


# The ServiceManager of the running OOo.
# It is cached in a global variable.
goServiceManager = False
pythonloader.DEBUG = 0
def getServiceManager( cHost="localhost", cPort="2002" ):
    """Get the ServiceManager from the running OpenOffice.org.
        Then retain it in the global variable goServiceManager for future use.
        This is similar to the GetProcessServiceManager() in OOo Basic.
    """
    global goServiceManager
    global pythonloader
    if not goServiceManager:
        # Get the uno component context from the PyUNO runtime
        oLocalContext = uno.getComponentContext()
        # Create the UnoUrlResolver on the Python side.

        # Connect to the running OpenOffice.org and get its context.
        if __name__<>"package":
            oLocalResolver = oLocalContext.ServiceManager.createInstanceWithContext(
                                    "com.sun.star.bridge.UnoUrlResolver", oLocalContext )
            oContext = oLocalResolver.resolve( "uno:socket,host=" + cHost + ",port=" + cPort + ";urp;StarOffice.ComponentContext" )
        # Get the ServiceManager object
            goServiceManager = oContext.ServiceManager
        else:
            goServiceManager=oLocalContext.ServiceManager

    return goServiceManager


#------------------------------------------------------------
#   Uno convenience functions
#   The stuff in this section is just to make
#    python progrmaming of OOo more like using OOo Basic.
#------------------------------------------------------------


# This is the same as ServiceManager.createInstance( ... )
def createUnoService( cClass ):
    """A handy way to create a global objects within the running OOo.
    Similar to the function of the same name in OOo Basic.
    """
    oServiceManager = getServiceManager()
    oObj = oServiceManager.createInstance( cClass )
    return oObj


# The StarDesktop object.  (global like in OOo Basic)
# It is cached in a global variable.
StarDesktop = None
def getDesktop():
    """An easy way to obtain the Desktop object from a running OOo.
    """
    global StarDesktop
    if StarDesktop == None:
        StarDesktop = createUnoService( "com.sun.star.frame.Desktop" )
    return StarDesktop
# preload the StarDesktop variable.
#getDesktop()


# The CoreReflection object.
# It is cached in a global variable.
goCoreReflection = False
def getCoreReflection():
    global goCoreReflection
    if not goCoreReflection:
        goCoreReflection = createUnoService( "com.sun.star.reflection.CoreReflection" )
    return goCoreReflection


def createUnoStruct( cTypeName ):
    """Create a UNO struct and return it.
    Similar to the function of the same name in OOo Basic.
    """
    oCoreReflection = getCoreReflection()
    # Get the IDL class for the type name
    oXIdlClass = oCoreReflection.forName( cTypeName )
    # Create the struct.
    oReturnValue, oStruct = oXIdlClass.createObject( None )
    return oStruct

#------------------------------------------------------------
#   API helpers
#------------------------------------------------------------

def hasUnoInterface( oObject, cInterfaceName ):
    """Similar to Basic's HasUnoInterfaces() function, but singular not plural."""

    # Get the Introspection service.
    oIntrospection = createUnoService( "com.sun.star.beans.Introspection" )

    # Now inspect the object to learn about it.
    oObjInfo = oIntrospection.inspect( oObject )

    # Obtain an array describing all methods of the object.
    oMethods = oObjInfo.getMethods( uno.getConstantByName( "com.sun.star.beans.MethodConcept.ALL" ) )
    # Now look at every method.
    for oMethod in oMethods:
        # Check the method's interface to see if
        #  these aren't the droids you're looking for.
        cMethodInterfaceName = oMethod.getDeclaringClass().getName()
        if cMethodInterfaceName == cInterfaceName:
            return True
    return False

def hasUnoInterfaces( oObject, *cInterfaces ):
    """Similar to the function of the same name in OOo Basic."""
    for cInterface in cInterfaces:
        if not hasUnoInterface( oObject, cInterface ):
            return False
    return True

#------------------------------------------------------------
#   High level general purpose functions
#------------------------------------------------------------


def makePropertyValue( cName=None, uValue=None, nHandle=None, nState=None ):
    """Create a com.sun.star.beans.PropertyValue struct and return it.
    """
    oPropertyValue = createUnoStruct( "com.sun.star.beans.PropertyValue" )

    if cName != None:
        oPropertyValue.Name = cName
    if uValue != None:
        oPropertyValue.Value = uValue
    if nHandle != None:
        oPropertyValue.Handle = nHandle
    if nState != None:
        oPropertyValue.State = nState

    return oPropertyValue


def makePoint( nX, nY ):
    """Create a com.sun.star.awt.Point struct."""
    oPoint = createUnoStruct( "com.sun.star.awt.Point" )
    oPoint.X = nX
    oPoint.Y = nY
    return oPoint


def makeSize( nWidth, nHeight ):
    """Create a com.sun.star.awt.Size struct."""
    oSize = createUnoStruct( "com.sun.star.awt.Size" )
    oSize.Width = nWidth
    oSize.Height = nHeight
    return oSize


def makeRectangle( nX, nY, nWidth, nHeight ):
    """Create a com.sun.star.awt.Rectangle struct."""
    oRect = createUnoStruct( "com.sun.star.awt.Rectangle" )
    oRect.X = nX
    oRect.Y = nY
    oRect.Width = nWidth
    oRect.Height = nHeight
    return oRect


def Array( *args ):
    """This is just sugar coating so that code from OOoBasic which
    contains the Array() function can work perfectly in python."""
    tArray = ()
    for arg in args:
        tArray += (arg,)
    return tArray


def loadComponentFromURL( cUrl, tProperties=() ):
    """Open or Create a document from it's URL.
    New documents are created from URL's such as:
        private:factory/sdraw
        private:factory/swriter
        private:factory/scalc
        private:factory/simpress
    """
    StarDesktop = getDesktop()
    oDocument = StarDesktop.loadComponentFromURL( cUrl, "_blank", 0, tProperties )
    return oDocument


#------------------------------------------------------------
#   Styles
#------------------------------------------------------------


def defineStyle( oDrawDoc, cStyleFamily, cStyleName, cParentStyleName=None ):
    """Add a new style to the style catalog if it is not already present.
    This returns the style object so that you can alter its properties.
    """

    oStyleFamily = oDrawDoc.getStyleFamilies().getByName( cStyleFamily )

    # Does the style already exist?
    if oStyleFamily.hasByName( cStyleName ):
        # then get it so we can return it.
        oStyle = oStyleFamily.getByName( cStyleName )
    else:
        # Create new style object.
        oStyle = oDrawDoc.createInstance( "com.sun.star.style.Style" )

        # Set its parent style
        if cParentStyleName != None:
            oStyle.setParentStyle( cParentStyleName )

        # Add the new style to the style family.
        oStyleFamily.insertByName( cStyleName, oStyle )

    return oStyle


def getStyle( oDrawDoc, cStyleFamily, cStyleName ):
    """Lookup and return a style from the document.
    """
    return oDrawDoc.getStyleFamilies().getByName( cStyleFamily ).getByName( cStyleName )

#------------------------------------------------------------
#   General Utility functions
#------------------------------------------------------------


def convertToURL( cPathname ):
    """Convert a Windows or Linux pathname into an OOo URL."""
    if len( cPathname ) > 1:
        if cPathname[1:2] == ":":
            cPathname = "/" + cPathname[0] + "|" + cPathname[2:]
    cPathname = cPathname.replace( "\\", "/" )
    cPathname = "file://" + cPathname
    return cPathname

# The global Awt Toolkit.
# This is initialized the first time it is needed.
#goAwtToolkit = createUnoService( "com.sun.star.awt.Toolkit" )
goAwtToolkit = None

def getAwtToolkit():
    global goAwtToolkit
    if goAwtToolkit == None:
        goAwtToolkit = createUnoService( "com.sun.star.awt.Toolkit" )
    return goAwtToolkit

# This class builds dialog boxes.
# This can be used in two different ways...
# 1. by subclassing it (elegant)
# 2. without subclassing it (less elegant)
class DBModalDialog:
    """Class to build a dialog box from the com.sun.star.awt.* services.
    This doesn't do anything you couldn't already do using OOo's UNO API,
     this just makes it much easier.
    You can change the dialog box size, position, title, etc.
    You can add controls, and listeners for those controls to the dialog box.
    This class can be used by subclassing it, or without subclassing it.
    """
    def __init__( self, nPositionX=None, nPositionY=None, nWidth=None, nHeight=None, cTitle=None ):
        self.oDialogModel = createUnoService( "com.sun.star.awt.UnoControlDialogModel" )
        if nPositionX != None:  self.oDialogModel.PositionX = nPositionX
        if nPositionY != None:  self.oDialogModel.PositionY = nPositionY
        if nWidth     != None:  self.oDialogModel.Width     = nWidth
        if nHeight    != None:  self.oDialogModel.Height    = nHeight
        if cTitle     != None:  self.oDialogModel.Title     = cTitle
        self.oDialogControl = createUnoService( "com.sun.star.awt.UnoControlDialog" )
        self.oDialogControl.setModel( self.oDialogModel )

    def release( self ):
        """Release resources.
        After calling this, you can no longer use this object.
        """
        self.oDialogControl.dispose()

    #--------------------------------------------------
    #   Dialog box adjustments
    #--------------------------------------------------

    def setDialogPosition( self, nX, nY ):
        self.oDialogModel.PositionX = nX
        self.oDialogModel.PositionY = nY

    def setDialogSize( self, nWidth, nHeight ):
        self.oDialogModel.Width = nWidth
        self.oDialogModel.Height = nHeight

    def setDialogTitle( self, cCaption ):
        self.oDialogModel.Title = cCaption

    def setVisible( self, bVisible ):
        self.oDialogControl.setVisible( bVisible )


    #--------------------------------------------------
    #   com.sun.star.awt.UnoControlButton
    #--------------------------------------------------

    # After you add a Button control, you can call self.setControlModelProperty()
    #  passing any of the properties for a...
    #       com.sun.star.awt.UnoControlButtonModel
    #       com.sun.star.awt.UnoControlDialogElement
    #       com.sun.star.awt.UnoControlModel
    def addButton( self, cCtrlName, nPositionX, nPositionY, nWidth, nHeight,
                       cLabel=None,
                       actionListenerProc=None,
                       nTabIndex=None ):
        self.addControl( "com.sun.star.awt.UnoControlButtonModel",
                         cCtrlName, nPositionX, nPositionY, nWidth, nHeight, bDropdown=None, bMultiSelection=None,
                         cLabel=cLabel,
                         nTabIndex=nTabIndex )
        if actionListenerProc != None:
            self.addActionListenerProc( cCtrlName, actionListenerProc )

    def setButtonLabel( self, cCtrlName, cLabel ):
        """Set the label of the control."""
        oControl = self.getControl( cCtrlName )
        oControl.setLabel( cLabel )

    #--------------------------------------------------
    #   com.sun.star.awt.UnoControlEditModel
    #--------------------------------------------------
    def addEdit( self, cCtrlName, nPositionX, nPositionY, nWidth, nHeight,
                        cText=None,
                        textListenerProc=None ):
        """Add a Edit control to the window."""
        self.addControl( "com.sun.star.awt.UnoControlEditModel",
            cCtrlName, nPositionX, nPositionY, nWidth, nHeight, bDropdown=None)

        if cText != None:
            self.setEditText( cCtrlName, cText )
        if textListenerProc != None:
            self.addTextListenerProc( cCtrlName, textListenerProc )

    #--------------------------------------------------
    #   com.sun.star.awt.UnoControlCheckBox
    #--------------------------------------------------

    # After you add a CheckBox control, you can call self.setControlModelProperty()
    #  passing any of the properties for a...
    #       com.sun.star.awt.UnoControlCheckBoxModel
    #       com.sun.star.awt.UnoControlDialogElement
    #       com.sun.star.awt.UnoControlModel
    def addCheckBox( self, cCtrlName, nPositionX, nPositionY, nWidth, nHeight,
                       cLabel=None,
                       itemListenerProc=None,
                       nTabIndex=None ):
        self.addControl( "com.sun.star.awt.UnoControlCheckBoxModel",
                         cCtrlName, nPositionX, nPositionY, nWidth, nHeight, bDropdown=None,  bMultiSelection=None,
                         cLabel=cLabel,
                         nTabIndex=nTabIndex )
        if itemListenerProc != None:
            self.addItemListenerProc( cCtrlName, itemListenerProc )

    def setEditText( self, cCtrlName, cText ):
        """Set the text of the edit box."""
        oControl = self.getControl( cCtrlName )
        oControl.setText( cText )

    def getEditText( self, cCtrlName):
        """Set the text of the edit box."""
        oControl = self.getControl( cCtrlName )
        return oControl.getText()

    def setCheckBoxLabel( self, cCtrlName, cLabel ):
        """Set the label of the control."""
        oControl = self.getControl( cCtrlName )
        oControl.setLabel( cLabel )

    def getCheckBoxState( self, cCtrlName ):
        """Get the state of the control."""
        oControl = self.getControl( cCtrlName )
        return oControl.getState();

    def setCheckBoxState( self, cCtrlName, nState ):
        """Set the state of the control."""
        oControl = self.getControl( cCtrlName )
        oControl.setState( nState )

    def enableCheckBoxTriState( self, cCtrlName, bTriStateEnable ):
        """Enable or disable the tri state mode of the control."""
        oControl = self.getControl( cCtrlName )
        oControl.enableTriState( bTriStateEnable )


    #--------------------------------------------------
    #   com.sun.star.awt.UnoControlFixedText
    #--------------------------------------------------

    def addFixedText( self, cCtrlName, nPositionX, nPositionY, nWidth, nHeight,
                        cLabel=None ):
        self.addControl( "com.sun.star.awt.UnoControlFixedTextModel",
                         cCtrlName, nPositionX, nPositionY, nWidth, nHeight,
                         bDropdown=None, bMultiSelection=None,
                         cLabel=cLabel )

        return self.getControl( cCtrlName )

    #--------------------------------------------------
    #   Add Controls to dialog
    #--------------------------------------------------

    def addControl( self, cCtrlServiceName,
                        cCtrlName, nPositionX, nPositionY, nWidth, nHeight,
                        bDropdown=None,
                        bMultiSelection=None,
                        cLabel=None,
                        nTabIndex=None,
                        sImagePath=None,
                         ):
        oControlModel = self.oDialogModel.createInstance( cCtrlServiceName )
        self.oDialogModel.insertByName( cCtrlName, oControlModel )
        # if negative coordinates are given for X or Y position,
        #  then make that coordinate be relative to the right/bottom
        #  edge of the dialog box instead of to the left/top.
        if nPositionX < 0: nPositionX = self.oDialogModel.Width  + nPositionX - nWidth
        if nPositionY < 0: nPositionY = self.oDialogModel.Height + nPositionY - nHeight
        oControlModel.PositionX = nPositionX
        oControlModel.PositionY = nPositionY
        oControlModel.Width = nWidth
        oControlModel.Height = nHeight
        oControlModel.Name = cCtrlName

        if bDropdown != None:
            oControlModel.Dropdown = bDropdown

        if bMultiSelection!=None:
            oControlModel.MultiSelection=bMultiSelection

        if cLabel != None:
            oControlModel.Label = cLabel

        if nTabIndex != None:
            oControlModel.TabIndex = nTabIndex

        if sImagePath != None:
            oControlModel.ImageURL = sImagePath
    #--------------------------------------------------
    #   Access controls and control models
    #--------------------------------------------------

    #--------------------------------------------------
    #   com.sun.star.awt.UnoContorlListBoxModel
    #--------------------------------------------------


    def addComboListBox( self, cCtrlName, nPositionX, nPositionY, nWidth, nHeight,
                        bDropdown=True,
                        bMultiSelection=False,
                        itemListenerProc=None,
                        actionListenerProc=None,
                        ):

        mod = self.addControl( "com.sun.star.awt.UnoControlListBoxModel",
                         cCtrlName, nPositionX, nPositionY, nWidth, nHeight,bDropdown,bMultiSelection )

        if itemListenerProc != None:
            self.addItemListenerProc( cCtrlName, itemListenerProc )

    def addListBoxItems( self, cCtrlName, tcItemTexts, nPosition=0 ):
        """Add a tupple of items to the ListBox at specified position."""
        oControl = self.getControl( cCtrlName )
        oControl.addItems( tcItemTexts, nPosition )

    def selectListBoxItem( self, cCtrlName, cItemText, bSelect=True ):
        """Selects/Deselects the ispecified item."""
        oControl = self.getControl( cCtrlName )
        return oControl.selectItem( cItemText, bSelect )

    def selectListBoxItemPos( self, cCtrlName, nItemPos, bSelect=True ):
        """Select/Deselect the item at the specified position."""
        oControl = self.getControl( cCtrlName )
        return oControl.selectItemPos( nItemPos, bSelect )

    def removeListBoxItems( self, cCtrlName, nPosition, nCount=1 ):
        """Remove items from a ListBox."""
        oControl = self.getControl( cCtrlName )
        oControl.removeItems( nPosition, nCount )

    def getListBoxItemCount( self, cCtrlName ):
        """Get the number of items in a ListBox."""
        oControl = self.getControl( cCtrlName )
        return oControl.getItemCount()

    def getListBoxSelectedItem( self, cCtrlName ):
        """Returns the currently selected item."""
        oControl = self.getControl( cCtrlName )
        return oControl.getSelectedItem()

    def getListBoxItem( self, cCtrlName, nPosition ):
        """Return the item at specified position within the ListBox."""
        oControl = self.getControl( cCtrlName )
        return oControl.getItem( nPosition )

    def getListBoxSelectedItemPos(self,cCtrlName):

        oControl = self.getControl( cCtrlName )
        return oControl.getSelectedItemPos()

    def getListBoxSelectedItems(self,cCtrlName):
        oControl = self.getControl( cCtrlName )
        return oControl.getSelectedItems()

    def getListBoxSelectedItemsPos(self,cCtrlName):

        oControl = self.getControl( cCtrlName )
        return oControl.getSelectedItemsPos()

    #--------------------------------------------------
    #   com.sun.star.awt.UnoControlComboBoxModel
    #--------------------------------------------------
    def addComboBox( self, cCtrlName, nPositionX, nPositionY, nWidth, nHeight,
                        bDropdown=True,
                        itemListenerProc=None,
                        actionListenerProc=None ):

        mod = self.addControl( "com.sun.star.awt.UnoControlComboBoxModel",
                         cCtrlName, nPositionX, nPositionY, nWidth, nHeight,bDropdown)
        if itemListenerProc != None:
            self.addItemListenerProc( cCtrlName, itemListenerProc )
        if actionListenerProc != None:
            self.addActionListenerProc( cCtrlName, actionListenerProc )


    def setComboBoxText( self, cCtrlName, cText ):
        """Set the text of the ComboBox."""
        oControl = self.getControl( cCtrlName )
        oControl.setText( cText )

    def getComboBoxText( self, cCtrlName):
        """Set the text of the ComboBox."""
        oControl = self.getControl( cCtrlName )
        return oControl.getText()

    def getComboBoxSelectedText( self, cCtrlName ):
        """Get the selected text of the ComboBox."""
        oControl = self.getControl( cCtrlName )
        return oControl.getSelectedText();

    def getControl( self, cCtrlName ):
        """Get the control (not its model) for a particular control name.
        The control returned includes the service com.sun.star.awt.UnoControl,
         and another control-specific service which inherits from it.
        """
        oControl = self.oDialogControl.getControl( cCtrlName )
        return oControl

    def getControlModel( self, cCtrlName ):
        """Get the control model (not the control) for a particular control name.
        The model returned includes the service UnoControlModel,
         and another control-specific service which inherits from it.
        """
        oControl = self.getControl( cCtrlName )
        oControlModel = oControl.getModel()
        return oControlModel
    #---------------------------------------------------
    #    com.sun.star.awt.UnoControlImageControlModel
    #---------------------------------------------------
    def addImageControl( self, cCtrlName, nPositionX, nPositionY, nWidth, nHeight,
                        sImagePath="",
                        itemListenerProc=None,
                        actionListenerProc=None ):

        mod = self.addControl( "com.sun.star.awt.UnoControlImageControlModel",
                         cCtrlName, nPositionX, nPositionY, nWidth, nHeight, sImagePath=sImagePath)

        if itemListenerProc != None:
            self.addItemListenerProc( cCtrlName, itemListenerProc )
        if actionListenerProc != None:
            self.addActionListenerProc( cCtrlName, actionListenerProc )


    #--------------------------------------------------
    #   Adjust properties of control models
    #--------------------------------------------------

    def setControlModelProperty( self, cCtrlName, cPropertyName, uValue ):
        """Set the value of a property of a control's model.
        This affects the control model, not the control.
        """
        oControlModel = self.getControlModel( cCtrlName )
        oControlModel.setPropertyValue( cPropertyName, uValue )

    def getControlModelProperty( self, cCtrlName, cPropertyName ):
        """Get the value of a property of a control's model.
        This affects the control model, not the control.
        """
        oControlModel = self.getControlModel( cCtrlName )
        return oControlModel.getPropertyValue( cPropertyName )

    #--------------------------------------------------
    #   Sugar coated property adjustments to control models.
    #--------------------------------------------------

    def setEnabled( self, cCtrlName, bEnabled=True ):
        """Supported controls...
            UnoControlButtonModel
            UnoControlCheckBoxModel
        """
        self.setControlModelProperty( cCtrlName, "Enabled", bEnabled )

    def getEnabled( self, cCtrlName ):
        """Supported controls...
            UnoControlButtonModel
            UnoControlCheckBoxModel
        """

        return self.getControlModelProperty( cCtrlName, "Enabled" )

    def setState( self, cCtrlName, nState ):
        """Supported controls...
            UnoControlButtonModel
            UnoControlCheckBoxModel
        """
        self.setControlModelProperty( cCtrlName, "State", nState )

    def getState( self, cCtrlName ):
        """Supported controls...
            UnoControlButtonModel
            UnoControlCheckBoxModel
        """
        return self.getControlModelProperty( cCtrlName, "State" )

    def setLabel( self, cCtrlName, cLabel ):
        """Supported controls...
            UnoControlButtonModel
            UnoControlCheckBoxModel
        """
        self.setControlModelProperty( cCtrlName, "Label", cLabel )

    def getLabel( self, cCtrlName ):
        """Supported controls...
            UnoControlButtonModel
            UnoControlCheckBoxModel
        """
        return self.getControlModelProperty( cCtrlName, "Label" )

    def setHelpText( self, cCtrlName, cHelpText ):
        """Supported controls...
            UnoControlButtonModel
            UnoControlCheckBoxModel
        """
        self.setControlModelProperty( cCtrlName, "HelpText", cHelpText )

    def getHelpText( self, cCtrlName ):
        """Supported controls...
            UnoControlButtonModel
            UnoControlCheckBoxModel
        """
        return self.getControlModelProperty( cCtrlName, "HelpText" )


    #--------------------------------------------------
    #   Adjust controls (not models)
    #--------------------------------------------------

    # The following apply to all controls which are a
    #   com.sun.star.awt.UnoControl

    def setDesignMode( self, cCtrlName, bDesignMode=True ):
        oControl = self.getControl( cCtrlName )
        oControl.setDesignMode( bDesignMode )

    def isDesignMode( self, cCtrlName, bDesignMode=True ):
        oControl = self.getControl( cCtrlName )
        return oControl.isDesignMode()

    def isTransparent( self, cCtrlName, bDesignMode=True ):
        oControl = self.getControl( cCtrlName )
        return oControl.isTransparent()


    # The following apply to all controls which are a
    #   com.sun.star.awt.UnoControlDialogElement

    def setPosition( self, cCtrlName, nPositionX, nPositionY ):
        self.setControlModelProperty( cCtrlName, "PositionX", nPositionX )
        self.setControlModelProperty( cCtrlName, "PositionY", nPositionY )
    def setPositionX( self, cCtrlName, nPositionX ):
        self.setControlModelProperty( cCtrlName, "PositionX", nPositionX )
    def setPositionY( self, cCtrlName, nPositionY ):
        self.setControlModelProperty( cCtrlName, "PositionY", nPositionY )
    def getPositionX( self, cCtrlName ):
        return self.getControlModelProperty( cCtrlName, "PositionX" )
    def getPositionY( self, cCtrlName ):
        return self.getControlModelProperty( cCtrlName, "PositionY" )

    def setSize( self, cCtrlName, nWidth, nHeight ):
        self.setControlModelProperty( cCtrlName, "Width", nWidth )
        self.setControlModelProperty( cCtrlName, "Height", nHeight )
    def setWidth( self, cCtrlName, nWidth ):
        self.setControlModelProperty( cCtrlName, "Width", nWidth )
    def setHeight( self, cCtrlName, nHeight ):
        self.setControlModelProperty( cCtrlName, "Height", nHeight )
    def getWidth( self, cCtrlName ):
        return self.getControlModelProperty( cCtrlName, "Width" )
    def getHeight( self, cCtrlName ):
        return self.getControlModelProperty( cCtrlName, "Height" )

    def setTabIndex( self, cCtrlName, nWidth, nTabIndex ):
        self.setControlModelProperty( cCtrlName, "TabIndex", nTabIndex )
    def getTabIndex( self, cCtrlName ):
        return self.getControlModelProperty( cCtrlName, "TabIndex" )

    def setStep( self, cCtrlName, nWidth, nStep ):
        self.setControlModelProperty( cCtrlName, "Step", nStep )
    def getStep( self, cCtrlName ):
        return self.getControlModelProperty( cCtrlName, "Step" )

    def setTag( self, cCtrlName, nWidth, cTag ):
        self.setControlModelProperty( cCtrlName, "Tag", cTag )
    def getTag( self, cCtrlName ):
        return self.getControlModelProperty( cCtrlName, "Tag" )

    def setEchoChar(self, cCtrlName , cVal):
        self.setControlModelProperty(cCtrlName, "EchoChar", cVal)
    def getEchoChar(self, cCtrlName):
        return self.setControlModelProperty(cCtrlName, "EchoChar")

    #--------------------------------------------------
    #   Add listeners to controls.
    #--------------------------------------------------

    # This applies to...
    #   UnoControlButton
    def addActionListenerProc( self, cCtrlName, actionListenerProc ):
        """Create an com.sun.star.awt.XActionListener object and add it to a control.
        A listener object is created which will call the python procedure actionListenerProc.
        The actionListenerProc can be either a method or a global procedure.
        The following controls support XActionListener:
            UnoControlButton
        """
        oControl = self.getControl( cCtrlName )
        oActionListener = ActionListenerProcAdapter( actionListenerProc )
        oControl.addActionListener( oActionListener )

    # This applies to...
    #   UnoControlCheckBox
    def addItemListenerProc( self, cCtrlName, itemListenerProc ):
        """Create an com.sun.star.awt.XItemListener object and add it to a control.
        A listener object is created which will call the python procedure itemListenerProc.
        The itemListenerProc can be either a method or a global procedure.
        The following controls support XActionListener:
            UnoControlCheckBox
        """
        oControl = self.getControl( cCtrlName )
        oActionListener = ItemListenerProcAdapter( itemListenerProc )
        oControl.addItemListener( oActionListener )

    #--------------------------------------------------
    #   Display the modal dialog.
    #--------------------------------------------------

    def doModalDialog( self, sObjName,sValue):
        """Display the dialog as a modal dialog."""
        self.oDialogControl.setVisible( True )
        if not sValue==None:
            self.selectListBoxItem( sObjName, sValue, True )
        self.oDialogControl.execute()

    def endExecute( self ):
        """Call this from within one of the listeners to end the modal dialog.
        For instance, the listener on your OK or Cancel button would call this to end the dialog.
        """
        self.oDialogControl.endExecute()

import urllib

def get_absolute_file_path( url ):
	url_unquoted = urllib.unquote(url)
	return os.name == 'nt' and url_unquoted[1:] or url_unquoted 

# This function reads the content of a file and return it to the caller
def read_data_from_file( filename ):
	fp = file( filename, "rb" )
	data = fp.read()
	fp.close()
	return data

# This function writes the content to a file
def write_data_to_file( filename, data ):
	fp = file( filename, 'wb' )
	fp.write( data )
	fp.close()

import logging
import tempfile
LOG_DEBUG='debug'
LOG_INFO='info'
LOG_WARNING='warn'
LOG_ERROR='error'
LOG_CRITICAL='critical'

def log_detail(self):
    import os
    logger = logging.getLogger()
    logfile_name = os.path.join(tempfile.gettempdir(), "report_designer.log")
    hdlr = logging.FileHandler(logfile_name)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.INFO)

class Logger(object):
    def log_write(self,name,level,msg):
        log = logging.getLogger(name)
        getattr(log,level)(msg)

    def shutdown(self):
        logging.shutdown()

import time
import socket
import xmlrpclib
#import tiny_socket
import re

class RPCGateway(object):
    def __init__(self, host, port, protocol):

        self.protocol = protocol
        self.host = host
        self.port = port

    def get_url(self):

        """Get the url
        """
        return "%s://%s:%s/"%(self.protocol, self.host, self.port)

    def listdb(self):
        """Get the list of databases.
        """
        pass

    def login(self, db, user, password):
        pass

    def execute(self, obj, method, *args):
        pass



class RPCSession(object):
    def __init__(self,url):

        m = re.match('^(http[s]?://|socket://)([\w.\-]+):(\d{1,5})$', url or '')

        host = m.group(2)
        port = m.group(3)
        protocol = m.group(1)
        if not m:
            return -1
        if protocol == 'http://' or protocol == 'http://':
            self.gateway = XMLRPCGateway(host, port, 'http')
        elif protocol == 'socket://':

            self.gateway = NETRPCGateway(host, port)

    def listdb(self):
        return self.gateway.listdb()

    def login(self, db, user, password):

        if password is None:
            return -1

        uid = self.gateway.login(db, user or '', password or '')

        if uid <= 0:
            return -1

        self.uid = uid
        self.db = db
        self.password = password
        self.open = True
        return uid


    def execute(self, obj, method, *args):
        try:
            result = self.gateway.execute(obj, method, *args)
            return self.__convert(result)
        except Exception,e:
          import traceback,sys
          info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))

    def __convert(self, result):

        if isinstance(result, basestring):
            # try to convert into unicode string
            try:
                return ustr(result)
            except Exception, e:
                return result

        elif isinstance(result, list):
            return [self.__convert(val) for val in result]

        elif isinstance(result, tuple):
            return tuple([self.__convert(val) for val in result])

        elif isinstance(result, dict):
            newres = {}
            for key, val in result.items():
                newres[key] = self.__convert(val)

            return newres

        else:
            return result

class XMLRPCGateway(RPCGateway):
    """XML-RPC implementation.
    """
    def __init__(self, host, port, protocol='http'):

        super(XMLRPCGateway, self).__init__(host, port, protocol)
        global rpc_url
        rpc_url =  self.get_url() + 'xmlrpc/'

    def listdb(self):
        global rpc_url
        sock = xmlrpclib.ServerProxy(rpc_url + 'db')
        try:
            return sock.list()
        except Exception, e:
            return -1

    def login(self, db, user, password):

        global rpc_url

        sock = xmlrpclib.ServerProxy(rpc_url + 'common')

        try:
            res = sock.login(db, user, password)
        except Exception, e:
            import traceback,sys
            info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            return -1

        return res

    def execute(self, sDatabase,UID,sPassword,obj, method, *args):
        global rpc_url

        sock = xmlrpclib.ServerProxy(rpc_url + 'object')

        return sock.execute(sDatabase,UID,sPassword, obj ,method,*args)



class NETRPCGateway(RPCGateway):
    def __init__(self, host, port):

        super(NETRPCGateway, self).__init__(host, port, 'socket')

    def listdb(self):
        sock = mysocket()
        try:
            sock.connect(self.host, self.port)
            sock.mysend(('db', 'list'))
            res = sock.myreceive()
            sock.disconnect()
            return res
        except Exception, e:
            return -1

    def login(self, db, user, password):
        sock =  mysocket()
        try:
            sock.connect(self.host, self.port)
            sock.mysend(('common', 'login', db, user, password))
            res = sock.myreceive()
            sock.disconnect()
        except Exception, e:
            return -1
        return res
    def execute(self,obj, method, *args):
        sock = mysocket()
        try:
            sock.connect(self.host, self.port)
            data=(('object', 'execute',obj,method,)+args)
            sock.mysend(data)
            res=sock.myreceive()
            sock.disconnect()
            return res

        except Exception,e:
            import traceback,sys
            info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))


# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import socket
import cPickle
import cStringIO
import marshal

class Myexception(Exception):
    def __init__(self, faultCode, faultString):
        self.faultCode = faultCode
        self.faultString = faultString
        self.args = (faultCode, faultString)

class mysocket:
    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
        self.sock.settimeout(120)
    def connect(self, host, port=False):
        if not port:
            protocol, buf = host.split('//')
            host, port = buf.split(':')
        self.sock.connect((host, int(port)))
    def disconnect(self):
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
    def mysend(self, msg, exception=False, traceback=None):

        msg = cPickle.dumps([msg,traceback])
        size = len(msg)
        self.sock.send('%8d' % size)
        self.sock.send(exception and "1" or "0")
        totalsent = 0
        while totalsent < size:
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError, "socket connection broken"
            totalsent = totalsent + sent
    def myreceive(self):
        buf=''
        while len(buf) < 8:
            chunk = self.sock.recv(8 - len(buf))
            if chunk == '':
                raise RuntimeError, "socket connection broken"
            buf += chunk
        size = int(buf)
        buf = self.sock.recv(1)
        if buf != "0":
            exception = buf
        else:
            exception = False
        msg = ''
        while len(msg) < size:
            chunk = self.sock.recv(size-len(msg))
            if chunk == '':
                raise RuntimeError, "socket connection broken"
            msg = msg + chunk
        msgio = cStringIO.StringIO(msg)
        unpickler = cPickle.Unpickler(msgio)
        unpickler.find_global = None
        res = unpickler.load()

        if isinstance(res[0],Exception):
            if exception:
                raise Myexception(str(res[0]), str(res[1]))
            raise res[0]
        else:
            return res[0]



import uno
import string
import unohelper
import xmlrpclib
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from lib.error import ErrorDialog
    from lib.functions import *
    from ServerParameter import *
    from lib.logreport import *
    from lib.rpc import *
    from LoginTest import *

    database="test_db1"
    uid = 3


#class RepeatIn:
class RepeatIn( unohelper.Base, XJobExecutor ):
    def __init__(self,sObject="",sVariable="",sFields="",sDisplayName="",bFromModify=False):
        # Interface Design
        LoginTest()
        self.logobj=Logger()
        if not loginstatus and __name__=="package":
            exit(1)

        self.win = DBModalDialog(60, 50, 180, 250, "RepeatIn Builder")
        self.win.addFixedText("lblVariable", 2, 12, 60, 15, "Objects to loop on :")
        self.win.addComboBox("cmbVariable", 180-120-2, 10, 120, 15,True, itemListenerProc=self.cmbVariable_selected)
        self.insVariable = self.win.getControl( "cmbVariable" )

        self.win.addFixedText("lblFields", 10, 32, 60, 15, "Field to loop on :")
        self.win.addComboListBox("lstFields", 180-120-2, 30, 120, 150, False,itemListenerProc=self.lstbox_selected)
        self.insField = self.win.getControl( "lstFields" )

        self.win.addFixedText("lblName", 12, 187, 60, 15, "Variable name :")
        self.win.addEdit("txtName", 180-120-2, 185, 120, 15,)

        self.win.addFixedText("lblUName", 8, 207, 60, 15, "Displayed name :")
        self.win.addEdit("txtUName", 180-120-2, 205, 120, 15,)

        self.win.addButton('btnOK',-2 ,-10,45,15,'Ok', actionListenerProc = self.btnOk_clicked )

        self.win.addButton('btnCancel',-2 - 45 - 5 ,-10,45,15,'Cancel', actionListenerProc = self.btnCancel_clicked )

        global passwd
        self.password = passwd
        global url
        self.sock=RPCSession(url)
        # Variable Declaration
        self.sValue=None
        self.sObj=None
        self.aSectionList=[]
        self.sGVariable=sVariable
        self.sGDisplayName=sDisplayName
        self.aItemList=[]
        self.aComponentAdd=[]
        self.aObjectList=[]
        self.aListRepeatIn=[]
        self.aVariableList=[]
        # Call method to perform Enumration on Report Document
        EnumDocument(self.aItemList,self.aComponentAdd)
        # Perform checking that Field-1 and Field - 4 is available or not alos get Combobox
        # filled if condition is true
        desktop = getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo = doc.getDocumentInfo()
        # Check weather Field-1 is available if not then exit from application
        self.sMyHost= ""

        if not docinfo.getUserFieldValue(3) == "" and not docinfo.getUserFieldValue(0)=="":
            self.sMyHost= docinfo.getUserFieldValue(0)
            self.count=0
            oParEnum = doc.getTextFields().createEnumeration()

            while oParEnum.hasMoreElements():
                oPar = oParEnum.nextElement()
                if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
                    self.count += 1

            getList(self.aObjectList, self.sMyHost,self.count)
            cursor = doc.getCurrentController().getViewCursor()
            text = cursor.getText()
            tcur = text.createTextCursorByRange(cursor)

            self.aVariableList.extend( filter( lambda obj: obj[:obj.find(" ")] == "List", self.aObjectList ) )

            for i in range(len(self.aItemList)):
                try:
                    anItem = self.aItemList[i][1]
                    component = self.aComponentAdd[i]

                    if component == "Document":
                        sLVal = anItem[anItem.find(",'") + 2:anItem.find("')")]
                        self.aVariableList.extend( filter( lambda obj: obj[:obj.find("(")] == sLVal, self.aObjectList ) )

                    if tcur.TextSection:
                        getRecersiveSection(tcur.TextSection,self.aSectionList)
                        if component in self.aSectionList:
                            sLVal = anItem[anItem.find(",'") + 2:anItem.find("')")]
                            self.aVariableList.extend( filter( lambda obj: obj[:obj.find("(")] == sLVal, self.aObjectList ) )

                    if tcur.TextTable:
                        if not component == "Document" and component[component.rfind(".") + 1:] == tcur.TextTable.Name:
                            VariableScope( tcur, self.aVariableList, self.aObjectList, self.aComponentAdd, self.aItemList, component )
                except :
                    import traceback,sys
                    info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                    self.logobj.log_write('RepeatIn', LOG_ERROR, info)
            self.bModify=bFromModify

            if self.bModify==True:

                if sObject=="":
                    self.insVariable.setText("List of "+docinfo.getUserFieldValue(3))
                    self.insField.addItem("objects",self.win.getListBoxItemCount("lstFields"))
                    self.win.setEditText("txtName", sVariable)
                    self.win.setEditText("txtUName",sDisplayName)
                    self.sValue= "objects"
                else:
                    sItem=""
		    for anObject in self.aObjectList:
			if anObject[:anObject.find("(")] == sObject:
			    sItem = anObject
			    self.insVariable.setText( sItem )

		    genTree(
			sItem[sItem.find("(")+1:sItem.find(")")],
			self.aListRepeatIn,
			self.insField,
			self.sMyHost,
			2,
			ending=['one2many','many2many'],
			recur=['one2many','many2many']
		    )

                    self.sValue= self.win.getListBoxItem("lstFields",self.aListRepeatIn.index(sFields))

            for var in self.aVariableList:

		if var[:8] <> 'List of ':
		    self.model_ids = self.sock.execute(database, uid, self.password, 'ir.model' ,  'search', [('model','=',var[var.find("(")+1:var.find(")")])])
                else:
		    self.model_ids = self.sock.execute(database, uid, self.password, 'ir.model' ,  'search', [('model','=',var[8:])])
                fields=['name','model']
                self.model_res = self.sock.execute(database, uid, self.password, 'ir.model', 'read', self.model_ids,fields)
                if self.model_res <> []:
		    if var[:8]<>'List of ':
                        self.insVariable.addItem(var[:var.find("(")+1] + self.model_res[0]['name'] + ")" ,self.insVariable.getItemCount())
                    else:
                        self.insVariable.addItem('List of ' + self.model_res[0]['name'] ,self.insVariable.getItemCount())
                else:
                    self.insVariable.addItem(var ,self.insVariable.getItemCount())

            self.win.doModalDialog("lstFields",self.sValue)
        else:
            ErrorDialog("Please Select Appropriate module" ,"Create new report from: \nOpenERP -> Open a New Report")
            self.win.endExecute()

    def lstbox_selected(self,oItemEvent):
        sItem=self.win.getListBoxSelectedItem("lstFields")
        sMain=self.aListRepeatIn[self.win.getListBoxSelectedItemPos("lstFields")]

        if self.bModify==True:
            self.win.setEditText("txtName", self.sGVariable)
            self.win.setEditText("txtUName",self.sGDisplayName)
        else:
	    self.win.setEditText("txtName",sMain[sMain.rfind("/")+1:])
	    self.win.setEditText("txtUName","|-."+sItem[sItem.rfind("/")+1:]+".-|")

    def cmbVariable_selected(self,oItemEvent):

        if self.count > 0 :

            desktop=getDesktop()
            doc =desktop.getCurrentComponent()
            docinfo=doc.getDocumentInfo()
            self.win.removeListBoxItems("lstFields", 0, self.win.getListBoxItemCount("lstFields"))
            sItem=self.win.getComboBoxText("cmbVariable")
            for var in self.aVariableList:
		if var[:8]=='List of ':
		    if var[:8]==sItem[:8]:
                        sItem = var
		elif var[:var.find("(")+1] == sItem[:sItem.find("(")+1]:
                    sItem = var
            self.aListRepeatIn=[]

	    data = ( sItem[sItem.rfind(" ") + 1:] == docinfo.getUserFieldValue(3) ) and docinfo.getUserFieldValue(3) or sItem[sItem.find("(")+1:sItem.find(")")]
	    genTree( data, self.aListRepeatIn, self.insField, self.sMyHost, 2, ending=['one2many','many2many'], recur=['one2many','many2many'] )

            self.win.selectListBoxItemPos("lstFields", 0, True )

        else:
            sItem=self.win.getComboBoxText("cmbVariable")
            for var in self.aVariableList:
                if var[:8]=='List of ' and var[:8] == sItem[:8]:
                    sItem = var
            if sItem.find(".")==-1:
                temp=sItem[sItem.rfind("x_"):]
            else:
                temp=sItem[sItem.rfind(".")+1:]
            self.win.setEditText("txtName",temp)
            self.win.setEditText("txtUName","|-."+temp+".-|")
            self.insField.addItem("objects",self.win.getListBoxItemCount("lstFields"))
            self.win.selectListBoxItemPos("lstFields", 0, True )

    def btnOk_clicked(self, oActionEvent):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        cursor = doc.getCurrentController().getViewCursor()
        selectedItem = self.win.getListBoxSelectedItem( "lstFields" )
        selectedItemPos = self.win.getListBoxSelectedItemPos( "lstFields" )
        txtName = self.win.getEditText( "txtName" )
        txtUName = self.win.getEditText( "txtUName" )
        if selectedItem != "" and txtName != "" and txtUName != "":
            sKey=u""+ txtUName
            if selectedItem == "objects":
                sValue=u"[[ repeatIn(" + selectedItem + ",'" + txtName + "') ]]"
            else:
                sObjName=self.win.getComboBoxText("cmbVariable")
                sObjName=sObjName[:sObjName.find("(")]
                sValue=u"[[ repeatIn(" + sObjName + self.aListRepeatIn[selectedItemPos].replace("/",".") + ",'" + txtName +"') ]]"

            if self.bModify == True:
                oCurObj = cursor.TextField
                oCurObj.Items = (sKey,sValue)
                oCurObj.update()
            else:
                oInputList = doc.createInstance("com.sun.star.text.TextField.DropDown")
                if self.win.getListBoxSelectedItem("lstFields") == "objects":
                    oInputList.Items = (sKey,sValue)
                    doc.Text.insertTextContent(cursor,oInputList,False)
                else:
                    sValue=u"[[ repeatIn(" + sObjName + self.aListRepeatIn[selectedItemPos].replace("/",".") + ",'" + txtName +"') ]]"
                    if cursor.TextTable==None:
                        oInputList.Items = (sKey,sValue)
                        doc.Text.insertTextContent(cursor,oInputList,False)
                    else:
                        oInputList.Items = (sKey,sValue)
                        widget = ( cursor.TextTable or selectedItem <> 'objects' ) and cursor.TextTable.getCellByName( cursor.Cell.CellName ) or doc.Text
                        widget.insertTextContent(cursor,oInputList,False)
                self.win.endExecute()
        else:
            ErrorDialog("Please Fill appropriate data in Object Field or Name field \nor select perticular value from the list of fields")

    def btnCancel_clicked( self, oActionEvent ):
        self.win.endExecute()

if __name__<>"package" and __name__=="__main__":
    RepeatIn()
elif __name__=="package":
    g_ImplementationHelper = unohelper.ImplementationHelper()
    g_ImplementationHelper.addImplementation( RepeatIn, "org.openoffice.openerp.report.repeatln", ("com.sun.star.task.Job",),)


import uno
import string
import unohelper
import xmlrpclib

from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from lib.functions import *
    from lib.error import ErrorDialog
    from LoginTest import *
    from lib.logreport import *
    from lib.rpc import *
    database="report"
    uid = 3


class Fields(unohelper.Base, XJobExecutor ):
    def __init__(self,sVariable="",sFields="",sDisplayName="",bFromModify=False):
        LoginTest()
        if not loginstatus and __name__=="package":
            exit(1)
        self.logobj=Logger()
        self.win = DBModalDialog(60, 50, 200, 225, "Field Builder")

        self.win.addFixedText("lblVariable", 27, 12, 60, 15, "Variable :")
        self.win.addComboBox("cmbVariable", 180-120-2, 10, 130, 15,True, itemListenerProc=self.cmbVariable_selected)
        self.insVariable = self.win.getControl( "cmbVariable" )

        self.win.addFixedText("lblFields", 10, 32, 60, 15, "Variable Fields :")
        self.win.addComboListBox("lstFields", 180-120-2, 30, 130, 150, False,True,itemListenerProc=self.lstbox_selected)
        self.insField = self.win.getControl( "lstFields" )

        self.win.addFixedText("lblUName", 8, 187, 60, 15, "Displayed name :")
        self.win.addEdit("txtUName", 180-120-2, 185, 130, 15,)

        self.win.addButton('btnOK',-5 ,-5,45,15,'Ok' ,actionListenerProc = self.btnOk_clicked )
        self.win.addButton('btnCancel',-5 - 45 - 5 ,-5,45,15,'Cancel' ,actionListenerProc = self.btnCancel_clicked )

        global passwd
        self.password = passwd
        global url
        self.sock=RPCSession(url)

        self.sValue=None
        self.sObj=None
        self.aSectionList=[]
        self.sGDisplayName=sDisplayName
        self.aItemList=[]
        self.aComponentAdd=[]
        self.aObjectList=[]
        self.aListFields=[]
        self.aVariableList=[]
        EnumDocument(self.aItemList,self.aComponentAdd)
        desktop=getDesktop()
        doc =desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        self.sMyHost= ""

        if not docinfo.getUserFieldValue(3) == "" and not docinfo.getUserFieldValue(0)=="":
            self.sMyHost = docinfo.getUserFieldValue(0)
            self.count = 0
            oParEnum = doc.getTextFields().createEnumeration()

            while oParEnum.hasMoreElements():
                oPar = oParEnum.nextElement()
                if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
                    self.count += 1

            getList(self.aObjectList, self.sMyHost,self.count)
            cursor = doc.getCurrentController().getViewCursor()
            text = cursor.getText()
            tcur = text.createTextCursorByRange(cursor)

            self.aVariableList.extend( filter( lambda obj: obj[:obj.find("(")] == "Objects", self.aObjectList ) )

            for i in range(len(self.aItemList)):
                try:
                    anItem = self.aItemList[i][1]
                    component = self.aComponentAdd[i]

                    if component == "Document":
                        sLVal = anItem[anItem.find(",'") + 2:anItem.find("')")]
                        self.aVariableList.extend( filter( lambda obj: obj[:obj.find("(")] == sLVal, self.aObjectList ) )

                    if tcur.TextSection:
                        getRecersiveSection(tcur.TextSection,self.aSectionList)
                        if component in self.aSectionList:
                            sLVal = anItem[anItem.find(",'") + 2:anItem.find("')")]
                            self.aVariableList.extend( filter( lambda obj: obj[:obj.find("(")] == sLVal, self.aObjectList ) )

                    if tcur.TextTable:
                        if not component == "Document" and component[component.rfind(".")+1:] == tcur.TextTable.Name:
                            VariableScope(tcur, self.aVariableList, self.aObjectList, self.aComponentAdd, self.aItemList, component)
                except:
                    import traceback,sys
                    info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                    self.logobj.log_write('Fields', LOG_ERROR, info)

            self.bModify=bFromModify
            if self.bModify==True:
                sItem=""
                for anObject in self.aObjectList:
                    if anObject[:anObject.find("(")] == sVariable:
                        sItem = anObject
                        self.insVariable.setText(sItem)
                genTree(
                    sItem[sItem.find("(")+1:sItem.find(")")],
                    self.aListFields,
                    self.insField,
                    self.sMyHost,
                    2,
                    ending_excl=['one2many','many2one','many2many','reference'],
                    recur=['many2one']
                )
                self.sValue= self.win.getListBoxItem("lstFields",self.aListFields.index(sFields))
            for var in self.aVariableList:

                    self.model_ids =self.sock.execute(database, uid, self.password, 'ir.model' ,  'search', [('model','=',var[var.find("(")+1:var.find(")")])])
                    fields=['name','model']
                    self.model_res = self.sock.execute(database, uid, self.password, 'ir.model', 'read', self.model_ids,fields)
                    if self.model_res <> []:
                        self.insVariable.addItem(var[:var.find("(")+1] + self.model_res[0]['name'] + ")" ,self.insVariable.getItemCount())
                    else:
                        self.insVariable.addItem(var ,self.insVariable.getItemCount())

            self.win.doModalDialog("lstFields",self.sValue)
        else:
            ErrorDialog("Please insert user define field Field-1 or Field-4","Just go to File->Properties->User Define \nField-1 Eg. http://localhost:8069 \nOR \nField-4 Eg. account.invoice")
            self.win.endExecute()

    def lstbox_selected(self,oItemEvent):
        try:

            desktop=getDesktop()
            doc =desktop.getCurrentComponent()
            docinfo=doc.getDocumentInfo()
            sItem= self.win.getComboBoxText("cmbVariable")
            for var in self.aVariableList:
                if var[:var.find("(")+1]==sItem[:sItem.find("(")+1]:
                    sItem = var
            sMain=self.aListFields[self.win.getListBoxSelectedItemPos("lstFields")]
            sObject=self.getRes(self.sock,sItem[sItem.find("(")+1:-1],sMain[1:])
            ids = self.sock.execute(database, uid, self.password, sObject ,  'search', [])
            res = self.sock.execute(database, uid, self.password, sObject , 'read',[ids[0]])
            self.win.setEditText("txtUName",res[0][sMain[sMain.rfind("/")+1:]])
        except:
            import traceback,sys
            info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            self.logobj.log_write('Fields', LOG_ERROR, info)
            self.win.setEditText("txtUName","TTT")
        if self.bModify:
            self.win.setEditText("txtUName",self.sGDisplayName)

    def getRes(self,sock ,sObject,sVar):
        desktop=getDesktop()
        doc =desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        res = sock.execute(database, uid, self.password, sObject , 'fields_get')
        key = res.keys()
        key.sort()
        myval=None
        if not sVar.find("/")==-1:
	    myval=sVar[:sVar.find("/")]
        else:
            myval=sVar
        if myval in key:
            if (res[myval]['type'] in ['many2one']):
                sObject = res[myval]['relation']
		return self.getRes(sock,res[myval]['relation'], sVar[sVar.find("/")+1:])
            else:
                return sObject

    def cmbVariable_selected(self,oItemEvent):
        if self.count > 0 :
            try:
                desktop=getDesktop()
                doc =desktop.getCurrentComponent()
                docinfo=doc.getDocumentInfo()
                self.win.removeListBoxItems("lstFields", 0, self.win.getListBoxItemCount("lstFields"))
                self.aListFields=[]
                tempItem = self.win.getComboBoxText("cmbVariable")
                for var in self.aVariableList:
                    if var[:var.find("(")] == tempItem[:tempItem.find("(")]:
                        sItem=var

                genTree(
                    sItem[sItem.find("(")+1:sItem.find(")")],
                    self.aListFields,
                    self.insField,
                    self.sMyHost,
                    2,
                    ending_excl=['one2many','many2one','many2many','reference'],
                    recur=['many2one']
                )
            except:
                import traceback,sys
                info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                self.logobj.log_write('Fields', LOG_ERROR, info)

    def btnOk_clicked( self, oActionEvent ):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        cursor = doc.getCurrentController().getViewCursor()
        for i in self.win.getListBoxSelectedItemsPos("lstFields"):
                itemSelected = self.aListFields[i]
                itemSelectedPos = i
                txtUName=self.win.getEditText("txtUName")
                sKey=u""+txtUName
                if itemSelected != "" and txtUName != "" and self.bModify==True :
                    txtUName=self.sGDisplayName
                    sKey=u""+txtUName
                    txtUName=self.sGDisplayName
                    oCurObj=cursor.TextField
                    sObjName=self.insVariable.getText()
                    sObjName=sObjName[:sObjName.find("(")]
                    sValue=u"[[ " + sObjName + self.aListFields[itemSelectedPos].replace("/",".") + " ]]"
                    oCurObj.Items = (sKey,sValue)
                    oCurObj.update()
                    self.win.endExecute()
                elif itemSelected != "" and txtUName != "" :

                    oInputList = doc.createInstance("com.sun.star.text.TextField.DropDown")
                    sObjName=self.win.getComboBoxText("cmbVariable")
                    sObjName=sObjName[:sObjName.find("(")]

                    widget = ( cursor.TextTable and cursor.TextTable.getCellByName( cursor.Cell.CellName ) or doc.Text )

                    sValue = u"[[ " + sObjName + self.aListFields[itemSelectedPos].replace("/",".") + " ]]"
                    oInputList.Items = (sKey,sValue)
                    widget.insertTextContent(cursor,oInputList,False)
                    self.win.endExecute()
                else:
                    ErrorDialog("Please Fill appropriate data in Name field \nor select perticular value from the list of fields")

    def btnCancel_clicked( self, oActionEvent ):
        self.win.endExecute()

if __name__<>"package" and __name__=="__main__":
    Fields()
elif __name__=="package":
    g_ImplementationHelper.addImplementation( Fields, "org.openoffice.openerp.report.fields", ("com.sun.star.task.Job",),)

import uno
import string
import unohelper
import xmlrpclib
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from lib.error import ErrorDialog
    from lib.functions import *
    database="test"
    uid = 3

class Expression(unohelper.Base, XJobExecutor ):
    def __init__(self,sExpression="",sName="", bFromModify=False):
        LoginTest()
        if not loginstatus and __name__=="package":
            exit(1)
        self.win = DBModalDialog(60, 50, 180, 65, "Expression Builder")
        self.win.addFixedText("lblExpression",17 , 10, 35, 15, "Expression :")
        self.win.addEdit("txtExpression", -5, 5, 123, 15)
        self.win.addFixedText("lblName", 2, 30, 50, 15, "Displayed Name :")
        self.win.addEdit("txtName", -5, 25, 123, 15)
        self.win.addButton( "btnOK", -5, -5, 40, 15, "OK", actionListenerProc = self.btnOk_clicked )
        self.win.addButton( "btnCancel", -5 - 40 -5, -5, 40, 15, "Cancel", actionListenerProc = self.btnCancel_clicked )
        self.bModify=bFromModify
        if self.bModify==True:
            self.win.setEditText("txtExpression",sExpression)
            self.win.setEditText("txtName",sName)
        self.win.doModalDialog("",None)


    def btnOk_clicked( self, oActionEvent ):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        text = doc.Text
        cursor = doc.getCurrentController().getViewCursor()
        if self.bModify==True:
            oCurObj=cursor.TextField
            sKey=u""+self.win.getEditText("txtName")
            sValue=u"[[ " + self.win.getEditText("txtExpression") + " ]]"
            oCurObj.Items = (sKey,sValue)
            oCurObj.update()
            self.win.endExecute()
        else:
            oInputList = doc.createInstance("com.sun.star.text.TextField.DropDown")
            if self.win.getEditText("txtName")!="" and self.win.getEditText("txtExpression")!="":
                sKey=u""+self.win.getEditText("txtName")
                sValue=u"[[ " + self.win.getEditText("txtExpression") + " ]]"
                if cursor.TextTable==None:
                    oInputList.Items = (sKey,sValue)
                    text.insertTextContent(cursor,oInputList,False)
                else:
                    oTable = cursor.TextTable
                    oCurCell = cursor.Cell
                    tableText = oTable.getCellByName( oCurCell.CellName )
                    oInputList.Items = (sKey,sValue)
                    tableText.insertTextContent(cursor,oInputList,False)
                self.win.endExecute()
            else:
                ErrorDialog("Please Fill appropriate data in Name field or \nExpression field")

    def btnCancel_clicked( self, oActionEvent ):
        self.win.endExecute()

if __name__<>"package" and __name__=="__main__":
    Expression()
elif __name__=="package":
    g_ImplementationHelper.addImplementation( Expression, "org.openoffice.openerp.report.expression", ("com.sun.star.task.Job",),)

import re
import uno
import string
import unohelper
import xmlrpclib
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from Expression import Expression
    from Fields import Fields
    from Repeatln import RepeatIn
    from lib.error import *
    database="test"
    uid = 3

class modify(unohelper.Base, XJobExecutor ):
    def __init__( self, ctx ):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"

        # Variable Declaration
        desktop = getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo = doc.getDocumentInfo()
        self.oVC = doc.CurrentController.getViewCursor()
        if not docinfo.getUserFieldValue(0)=="":
            self.sMyHost= docinfo.getUserFieldValue(0)
        else:
            ErrorDialog(
		"Please insert user define field Field-1",
		"Just go to File->Properties->User Define \n"
		"Field-1 Eg. http://localhost:8069"
	    )
            exit(1)

        # Check weather Field-4 is available or not otherwise exit from application
        if not docinfo.getUserFieldValue(3) == "" and not docinfo.getUserFieldValue(0)=="":
            if self.oVC.TextField:
                self.oCurObj=self.oVC.TextField
		item = self.oCurObj.Items[0]

		kind, group1, group2 = self.getOperation(self.oCurObj.Items[1] )

		start_group1 = group1[:group1.find(".")]
		stop_group1 = group1[group1.find("."):].replace(".", "/")

                if kind == "field":
		    Fields( start_group1, stop_group1, item, True )
                elif kind == "expression":
                    Expression( group1, item, True )
                elif kind == "repeatIn":
		    RepeatIn( start_group1, group2, stop_group1, item, True )
            else:
                ErrorDialog(
		    "Please place your cursor at begaining of field \n"
		    "which you want to modify",""
		)

        else:
            ErrorDialog(
		"Please insert user define field Field-1 or Field-4",
		"Just go to File->Properties->User Define \n"
		"Field-1 Eg. http://localhost:8069 \n"
		"OR \n"
		"Field-4 Eg. account.invoice"
	    )
            exit(1)

    def getOperation(self, str):
        #str = "[[ RepeatIn(objects, 'variable') ]]" #repeatIn
        #str = "[[ saleorder.partner_id.name ]]" # field
        #str = "[[ some thing complex ]]" # expression
        method1 = lambda x: (u'repeatIn', x.group(1), x.group(2))
        method2 = lambda x: (u'field', x.group(1), None)
        method3 = lambda x: (u'expression', x.group(1), None)
        regexes = [
	    ('\\[\\[ *repeatIn\\( *(.+)*, *\'([a-zA-Z0-9_]+)\' *\\) *\\]\\]', method1),
	    ('\\[\\[ *([a-zA-Z0-9_\.]+) *\\]\\]', method2),
	    ('\\[\\[ *(.+) *\\]\\]', method3)
        ]
        for (rule,method) in regexes:
	    res = re.match(rule, str)
	    if res:
		return method(res)

if __name__<>"package":
    modify(None)
else:
    g_ImplementationHelper.addImplementation( modify, "org.openoffice.openerp.report.modify", ("com.sun.star.task.Job",),)

import uno
import string
import unohelper
import xmlrpclib
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from lib.error import ErrorDialog
    from lib.functions import *
    from lib.logreport import *
    from lib.rpc import *
    from Change import *
    database="test"

class ServerParameter( unohelper.Base, XJobExecutor ):
    def __init__(self,ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        desktop=getDesktop()
        log_detail(self)
        self.logobj=Logger()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        self.win=DBModalDialog(60, 50, 160, 108, "Server Connection Parameter")

        self.win.addFixedText("lblVariable", 2, 12, 35, 15, "Server URL")
        if docinfo.getUserFieldValue(0)=="":
            docinfo.setUserFieldValue(0,"http://localhost:8069")
        self.win.addEdit("txtHost",-34,9,91,15,docinfo.getUserFieldValue(0))
        self.win.addButton('btnChange',-2 ,9,30,15,'Change', actionListenerProc = self.btnChange_clicked )

        self.win.addFixedText("lblDatabaseName", 6, 31, 31, 15, "Database")
        #self.win.addFixedText("lblMsg", -2,28,123,15)
#        self.win.addComboListBox("lstDatabase", -2,28,123,15, True)
#        self.lstDatabase = self.win.getControl( "lstDatabase" )
        #self.win.selectListBoxItem( "lstDatabase", docinfo.getUserFieldValue(2), True )
        #self.win.setEnabled("lblMsg",False)

        self.win.addFixedText("lblLoginName", 17, 51, 20, 15, "Login")
        self.win.addEdit("txtLoginName",-2,48,123,15,docinfo.getUserFieldValue(1))

        self.win.addFixedText("lblPassword", 6, 70, 31, 15, "Password")
        self.win.addEdit("txtPassword",-2,67,123,15,)
        self.win.setEchoChar("txtPassword",42)


        self.win.addButton('btnOK',-2 ,-5, 60,15,'Connect' ,actionListenerProc = self.btnOk_clicked )

        self.win.addButton('btnCancel',-2 - 60 - 5 ,-5, 35,15,'Cancel' ,actionListenerProc = self.btnCancel_clicked )
        sValue=""
        if docinfo.getUserFieldValue(0)<>"":
            global url
            global result
            url=docinfo.getUserFieldValue(0)
            self.sock=RPCSession(url)
            res=self.sock.listdb()
            result=res
            if res == -1:
                self.win.addEdit("lstDatabase",-2,28,123,15)
#                sValue="Could not connect to the server!"
#                self.lstDatabase.addItem("Could not connect to the server!",0)
            elif res == 0:
                sValue="No Database found !!!"
                self.lstDatabase.addItem("No Database found !!!",0)
            else:
                self.win.addComboListBox("lstDatabase", -2,28,123,15, True)
                self.lstDatabase = self.win.getControl( "lstDatabase" )
                self.win.removeListBoxItems("lstDatabase", 0, self.win.getListBoxItemCount("lstDatabase"))
                for i in range(len(res)):
                    self.lstDatabase.addItem(res[i],i)
                sValue = database
        if sValue:
            self.win.doModalDialog("lstDatabase",sValue)
        else:
            self.win.doModalDialog("lstDatabase",None)

        #self.win.doModalDialog("lstDatabase",docinfo.getUserFieldValue(2))

    def btnOk_clicked(self,oActionEvent):


        sLogin=self.win.getEditText("txtLoginName")
        sPassword=self.win.getEditText("txtPassword")
        global url
        global result
        if result==-1:
            sDatabase=self.win.getEditText("lstDatabase")
        else:
            sDatabase=self.win.getListBoxSelectedItem("lstDatabase")
        self.sock=RPCSession(url)
        UID = self.sock.login(sDatabase,sLogin,sPassword)
        if not UID :
            ErrorDialog("Connection Refuse...","Please enter valid Login/Password")
            self.win.endExecute()
        try:

            ids  = self.sock.execute(sDatabase,UID,sPassword, 'res.groups' ,  'search', [('name','=','OpenOfficeReportDesigner')])
            ids_module =self.sock.execute(sDatabase, UID, sPassword, 'ir.module.module', 'search', [('name','=','base_report_designer'),('state', '=', 'installed')])
            dict_groups =self.sock.execute(sDatabase, UID,sPassword, 'res.groups' , 'read',ids,['users'])
        except :
            import traceback,sys
            info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            self.logobj.log_write('ServerParameter', LOG_ERROR, info)

        if not len(ids) :
            ErrorDialog("Group Not Found!!!  Create a group  named  \n\n"'"OpenOfficeReportDesigner"'"  \n\n  ","","Group Name Error")
            self.logobj.log_write('Group Error',LOG_WARNING, ':Create a  group OpenOfficeReportDesigner   using database %s' % (sDatabase))
            self.win.endExecute()
        if not len(ids_module):
            ErrorDialog("Please Install base_report_designer module", "", "Module Uninstalled Error")
            self.logobj.log_write('Module Not Found',LOG_WARNING, ':base_report_designer not install in  database %s' % (sDatabase))
            self.win.endExecute()

        if UID not in dict_groups[0]['users']:
            ErrorDialog("Connection Refuse...","You have not access these Report Designer")
            self.logobj.log_write('Connection Refuse',LOG_WARNING, " Not Access Report Designer ")
            self.win.endExecute()
        else:
            desktop=getDesktop()
            doc = desktop.getCurrentComponent()
            docinfo=doc.getDocumentInfo()
            docinfo.setUserFieldValue(0,self.win.getEditText("txtHost"))
            docinfo.setUserFieldValue(1,self.win.getEditText("txtLoginName"))
            global passwd
            passwd=self.win.getEditText("txtPassword")
            global loginstatus
            loginstatus=True
            global database
            database=sDatabase
            global uid
            uid=UID
            #docinfo.setUserFieldValue(2,self.win.getListBoxSelectedItem("lstDatabase"))
            #docinfo.setUserFieldValue(3,"")

            ErrorDialog(" You can start creating your report in \n  \t the current document.","After Creating  sending to the server.","Message")
            self.logobj.log_write('successful login',LOG_INFO, ':successful login from %s  using database %s' % (sLogin, sDatabase))
            self.win.endExecute()

    def btnCancel_clicked( self, oActionEvent ):
        self.win.endExecute()

    def btnChange_clicked(self,oActionEvent):
        aVal=[]
        url= self.win.getEditText("txtHost")
        Change(aVal,url)
        if aVal[1]== -1:
           self.win.getEditText("lstDatabase")
        elif aVal[1]==0:
            ErrorDialog(aVal[0],"")
        else:
            self.win.setEditText("txtHost",aVal[0])
            self.win.removeListBoxItems("lstDatabase", 0, self.win.getListBoxItemCount("lstDatabase"))
            for i in range(len(aVal[1])):
                self.lstDatabase.addItem(aVal[1][i],i)


if __name__<>"package" and __name__=="__main__":
    ServerParameter(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( ServerParameter, "org.openoffice.openerp.report.serverparam", ("com.sun.star.task.Job",),)

if __name__<>"package":
    from lib.gui import *
    from lib.functions import *
    from lib.rpc import *

class Change:
    def __init__(self, aVal= None, sURL=""):
        self.win=DBModalDialog(60, 50, 120, 90, "Connect to Open ERP Server")

        self.win.addFixedText("lblVariable", 38, 12, 60, 15, "Server")

        self.win.addEdit("txtHost",-2,9,60,15,sURL[sURL.find("/")+2:sURL.rfind(":")])

        self.win.addFixedText("lblReportName",45 , 31, 60, 15, "Port")
        self.win.addEdit("txtPort",-2,28,60,15,sURL[sURL.rfind(":")+1:])

        self.win.addFixedText("lblLoginName", 2, 51, 60, 15, "Protocol Connection")

        self.win.addComboListBox("lstProtocol", -2, 48, 60, 15, True)
        self.lstProtocol = self.win.getControl( "lstProtocol" )

#        self.lstProtocol.addItem( "XML-RPC", 0)
        #self.lstProtocol.addItem( "XML-RPC secure", 1)
        #self.lstProtocol.addItem( "NET-RPC (faster)", 2)

        self.win.addButton( 'btnOK', -2, -5, 30, 15, 'Ok', actionListenerProc = self.btnOk_clicked )

        self.win.addButton( 'btnCancel', -2 - 30 - 5 ,-5, 30, 15, 'Cancel', actionListenerProc = self.btnCancel_clicked )
        self.aVal=aVal
        self.protocol = {
            'XML-RPC': 'http://',
            'XML-RPC secure': 'https://',
            'NET-RPC': 'socket://',
        }
        for i in self.protocol.keys():
            self.lstProtocol.addItem(i,self.lstProtocol.getItemCount() )

        sValue=self.protocol.keys()[0]
        if sURL<>"":
            sValue=self.protocol.keys()[self.protocol.values().index(sURL[:sURL.find("/")+2])]

        self.win.doModalDialog( "lstProtocol", sValue)

    def btnOk_clicked(self,oActionEvent):
        global url
        url = self.protocol[self.win.getListBoxSelectedItem("lstProtocol")]+self.win.getEditText("txtHost")+":"+self.win.getEditText("txtPort")
        self.sock=RPCSession(url)
        res=self.sock.listdb()
        if res == -1:
            self.aVal.append(url)
        elif res == 0:
            self.aVal.append("No Database found !!!")
        else:
            self.aVal.append(url)
        self.aVal.append(res)
        self.win.endExecute()

    def btnCancel_clicked( self, oActionEvent ):
        self.win.endExecute()


import uno
import string
import unohelper
import xmlrpclib

from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from lib.error import ErrorDialog
    from lib.functions import *
    from lib.logreport import *
    from LoginTest import *
    from lib.rpc import *
    database="test"
    uid = 3
#
#
#
# Start OpenOffice.org, listen for connections and open testing document
#
#
class NewReport(unohelper.Base, XJobExecutor):
    def __init__(self,ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        LoginTest()
        self.logobj=Logger()
        if not loginstatus and __name__=="package":
            exit(1)
        self.win=DBModalDialog(60, 50, 180, 115, "Open New Report")
        self.win.addFixedText("lblModuleSelection", 2, 2, 60, 15, "Module Selection")
        self.win.addComboListBox("lstModule", -2,13,176,80 , False)
        self.lstModule = self.win.getControl( "lstModule" )
        self.aModuleName=[]
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()

        global passwd
        self.password = passwd
        global url
        self.sock=RPCSession(url)
        ids = self.sock.execute(database, uid, self.password, 'ir.model' , 'search',[])
        fields = [ 'model','name']
        res = self.sock.execute(database, uid, self.password, 'ir.model' , 'read', ids, fields)
        res.sort(lambda x, y: cmp(x['name'],y['name']))

        for i in range(len(res)):
            self.lstModule.addItem(res[i]['name'],self.lstModule.getItemCount())
            self.aModuleName.append(res[i]['model'])
        self.win.addButton('btnOK',-2 ,-5, 70,15,'Use Module in Report' ,actionListenerProc = self.btnOk_clicked )
        self.win.addButton('btnCancel',-2 - 70 - 5 ,-5, 35,15,'Cancel' ,actionListenerProc = self.btnCancel_clicked )
        self.win.doModalDialog("",None)

    def btnOk_clicked(self,oActionEvent):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        docinfo.setUserFieldValue(3,self.aModuleName[self.lstModule.getSelectedItemPos()])
        self.logobj.log_write('Module Name',LOG_INFO, ':Module use in creating a report %s  using database %s' % (self.aModuleName[self.lstModule.getSelectedItemPos()], database))
        self.win.endExecute()

    def btnCancel_clicked( self, oActionEvent ):
        self.win.endExecute()

if __name__<>"package" and __name__=="__main__":
    NewReport(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( \
            NewReport,
            "org.openoffice.openerp.report.opennewreport",
            ("com.sun.star.task.Job",),)

if __name__<>"package":
    from ServerParameter import *
    from lib.gui import *

class LoginTest:
    def __init__(self):
        if not loginstatus:
            ServerParameter(None)



import uno
import string
import unohelper
import xmlrpclib
import base64, tempfile


from com.sun.star.task import XJobExecutor
import os
import sys
if __name__<>'package':
    from lib.gui import *
    from lib.error import *
    from LoginTest import *
    from lib.logreport import *
    from lib.rpc import *
    database="test"
    uid = 3

#
class ModifyExistingReport(unohelper.Base, XJobExecutor):
    def __init__(self,ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"

        LoginTest()
        if not loginstatus and __name__=="package":
            exit(1)

        self.win = DBModalDialog(60, 50, 180, 120, "Modify Existing Report")
        self.win.addFixedText("lblReport", 2, 3, 60, 15, "Report Selection")
        self.win.addComboListBox("lstReport", -1,15,178,80 , False )
        self.lstReport = self.win.getControl( "lstReport" )
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        self.logobj=Logger()
        self.hostname = docinfo.getUserFieldValue(0)
        global passwd
        self.password = passwd
        global url
        self.sock=RPCSession(url)
        # Open a new connexion to the server


        ids = self.sock.execute(database, uid, self.password, 'ir.module.module', 'search', [('name','=','base_report_designer'),('state', '=', 'installed')])
        if not len(ids):
            ErrorDialog("Please Install base_report_designer module", "", "Module Uninstalled Error")
            exit(1)

        ids = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'search', [('report_xsl', '=', False),('report_xml', '=', False)])

        fields=['id', 'name','report_name','model']

        self.reports = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'read', ids, fields)
        self.report_with_id = []

        for report in self.reports:
            if report['name']<>"":
                model_ids = self.sock.execute(database, uid, self.password, 'ir.model' ,  'search', [('model','=', report['model'])])
                model_res_other =self.sock.execute(database, uid, self.password, 'ir.model', 'read', model_ids, [ 'name', 'model' ] )
                if model_res_other <> []:
                    name = model_res_other[0]['name'] + " - " + report['name']
                else:
                    name = report['name'] + " - " + report['model']
                self.report_with_id.append( (report['id'], name, report['model'] ) )

        self.report_with_id.sort( lambda x, y: cmp( x[1], y[1] ) )

        for id, report_name, model_name in self.report_with_id:
            self.lstReport.addItem( report_name, self.lstReport.getItemCount() )

        self.win.addButton('btnSave',10,-5,50,15,'Open Report' ,actionListenerProc = self.btnOk_clicked )
        self.win.addButton('btnCancel',-10 ,-5,50,15,'Cancel' ,actionListenerProc = self.btnCancel_clicked )
        self.win.addButton('btnDelete',15 -80 ,-5,50,15,'Delete Report',actionListenerProc = self.btnDelete_clicked)
        self.win.doModalDialog("lstReport",self.report_with_id[0][1] )

    def btnOk_clicked(self, oActionEvent):
        try:
            desktop=getDesktop()
            doc = desktop.getCurrentComponent()
            docinfo=doc.getDocumentInfo()

            selectedItemPos = self.win.getListBoxSelectedItemPos( "lstReport" )
            id = self.report_with_id[ selectedItemPos ][0]

            res = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'report_get', id)

            if res['file_type'] in ['sxw','odt'] :
               file_type = res['file_type']
            else :
               file_type = 'sxw'

            fp_name = tempfile.mktemp('.'+file_type)
            fp_name1="r"+fp_name
            fp_path=os.path.join(fp_name1).replace("\\","/")
            fp_win=fp_path[1:]

            filename = ( os.name == 'nt' and fp_win or fp_name )
            if res['report_sxw_content']:
                write_data_to_file( filename, base64.decodestring(res['report_sxw_content']))
            url = "file:///%s" % filename

            arr=Array(makePropertyValue("MediaType","application/vnd.sun.xml.writer"),)
            oDoc2 = desktop.loadComponentFromURL(url, "openerp", 55, arr)
            docinfo2=oDoc2.getDocumentInfo()
            docinfo2.setUserFieldValue(0, self.hostname)
            docinfo2.setUserFieldValue(1,self.password)
            docinfo2.setUserFieldValue(2,id)
            docinfo2.setUserFieldValue(3,self.report_with_id[selectedItemPos][2])

            oParEnum = oDoc2.getTextFields().createEnumeration()
            while oParEnum.hasMoreElements():
                oPar = oParEnum.nextElement()
                if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
                    oPar.SelectedItem = oPar.Items[0]
                    oPar.update()
            if oDoc2.isModified():
                if oDoc2.hasLocation() and not oDoc2.isReadonly():
                    oDoc2.store()

            ErrorDialog("Download is Completed","Your file has been placed here :\n"+ fp_name,"Download Message")
            obj=Logger()
            obj.log_write('Modify Existing Report',LOG_INFO, ':successful download report  %s  using database %s' % (self.report_with_id[selectedItemPos][2], database))
        except Exception, e:
            ErrorDialog("Report has not been downloaded", "Report: %s\nDetails: %s" % ( fp_name, str(e) ),"Download Message")
            import traceback,sys
            info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            self.logobj.log_write('ModifyExistingReport', LOG_ERROR, info)

        self.win.endExecute()

    def btnCancel_clicked( self, oActionEvent ):
        self.win.endExecute()

    def btnDelete_clicked( self, oActionEvent ):
         desktop=getDesktop()
         doc = desktop.getCurrentComponent()
         docinfo=doc.getDocumentInfo()

         selectedItemPos = self.win.getListBoxSelectedItemPos( "lstReport" )
         name=self.win.getListBoxSelectedItem ("lstReport")
         id = self.report_with_id[ selectedItemPos ][0]
         temp = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'unlink', id,)
         str_value='ir.actions.report.xml,'+str(id)
         ids = self.sock.execute(database, uid, self.password, 'ir.values' ,  'search',[('value','=',str_value)])
         if ids:
              rec = self.sock.execute(database, uid, self.password, 'ir.values', 'unlink', ids,)
         else :
            pass
         if temp:
              ErrorDialog("Report","Report has been Delete:\n "+name,"Message")
              self.logobj.log_write('Delete Report',LOG_INFO, ':successful delete report  %s  using database %s' % (name, database))

         else:
             ErrorDialog("Report","Report has not Delete:\n"+name," Message")
         self.win.endExecute()



if __name__<>"package" and __name__=="__main__":
    ModifyExistingReport(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( ModifyExistingReport, "org.openoffice.openerp.report.modifyreport", ("com.sun.star.task.Job",),)


import uno
import string
import unohelper
import random
import xmlrpclib
import base64, tempfile
from com.sun.star.task import XJobExecutor
import os
import sys
if __name__<>'package':
    from lib.gui import *
    from lib.error import *
    from lib.functions import *
    from lib.logreport import *
    from lib.tools import *
    from LoginTest import *
    from lib.rpc import *
    database="report"
    uid = 3

#
#
class SendtoServer(unohelper.Base, XJobExecutor):
    Kind = {
        'PDF' : 'pdf',
        'OpenOffice': 'sxw',
        'HTML' : 'html'
    }

    def __init__(self,ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        LoginTest()
        self.logobj=Logger()
        if not loginstatus and __name__=="package":
            exit(1)

        global passwd
        self.password = passwd
        global url
        self.sock=RPCSession(url)
        desktop=getDesktop()
        oDoc2 = desktop.getCurrentComponent()
        docinfo=oDoc2.getDocumentInfo()

        self.ids = self.sock.execute(database, uid, self.password, 'ir.module.module', 'search', [('name','=','base_report_designer'),('state', '=', 'installed')])
        if not len(self.ids):
            ErrorDialog("Please Install base_report_designer module", "", "Module Uninstalled Error")
            exit(1)

        report_name = ""
        name=""
        if docinfo.getUserFieldValue(2)<>"" :
            try:
                fields=['name','report_name']
                self.res_other = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'read', [int(docinfo.getUserFieldValue(2))],fields)
                name = self.res_other[0]['name']
                report_name = self.res_other[0]['report_name']
            except:
                import traceback,sys
                info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                self.logob.log_write('ServerParameter', LOG_ERROR, info)
        elif docinfo.getUserFieldValue(3) <> "":
            name = ""
            result =  "rnd"
            for i in range(5):
                result =result + random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890')

            report_name = docinfo.getUserFieldValue(3) + "." + result
        else:
            ErrorDialog("Please select appropriate module...","Note: use OpenERP Report -> Open a new Report", "Module selection ERROR");
            exit(1)

        self.win = DBModalDialog(60, 50, 180, 100, "Send To Server")
        self.win.addFixedText("lblName",10 , 9, 40, 15, "Report Name :")
        self.win.addEdit("txtName", -5, 5, 123, 15,name)
        self.win.addFixedText("lblReportName", 2, 30, 50, 15, "Technical Name :")
        self.win.addEdit("txtReportName", -5, 25, 123, 15,report_name)
        self.win.addCheckBox("chkHeader", 51, 45, 70 ,15, "Corporate Header")
        self.win.addFixedText("lblResourceType", 2 , 60, 50, 15, "Select Rpt. Type :")
        self.win.addComboListBox("lstResourceType", -5, 58, 123, 15,True,itemListenerProc=self.lstbox_selected)
        self.lstResourceType = self.win.getControl( "lstResourceType" )
        self.txtReportName=self.win.getControl( "txtReportName" )
        self.txtReportName.Enable=False
        for kind in self.Kind.keys():
            self.lstResourceType.addItem( kind, self.lstResourceType.getItemCount() )

        self.win.addButton( "btnSend", -5, -5, 80, 15, "Send Report to Server", actionListenerProc = self.btnOk_clicked)
        self.win.addButton( "btnCancel", -5 - 80 -5, -5, 40, 15, "Cancel", actionListenerProc = self.btnCancel_clicked)

        self.win.doModalDialog("lstResourceType", self.Kind.keys()[0])

    def lstbox_selected(self,oItemEvent):
        pass

    def btnCancel_clicked( self, oActionEvent ):
        self.win.endExecute()

    def btnOk_clicked(self, oActionEvent):
        if self.win.getEditText("txtName") <> "" and self.win.getEditText("txtReportName") <> "":
            desktop=getDesktop()
            oDoc2 = desktop.getCurrentComponent()
            docinfo=oDoc2.getDocumentInfo()
            self.getInverseFieldsRecord(1)
            fp_name = tempfile.mktemp('.'+"sxw")
            if not oDoc2.hasLocation():
                oDoc2.storeAsURL("file://"+fp_name,Array(makePropertyValue("MediaType","application/vnd.sun.xml.writer"),))

            if docinfo.getUserFieldValue(2)=="":
                name=self.win.getEditText("txtName"),
                name_id={}
                try:
                    name_id = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml' , 'search',[('name','=',name)])
                    if not name_id:
                        id=self.getID()
                        docinfo.setUserFieldValue(2,id)
                        rec = {
                                'name': self.win.getEditText("txtReportName"),
                                'key': 'action',
                                'model': docinfo.getUserFieldValue(3),
                                'value': 'ir.actions.report.xml,'+str(id),
                                'key2': 'client_print_multi',
                                'object': True
                            }
                        res = self.sock.execute(database, uid, self.password, 'ir.values' , 'create',rec )
                    else :
                        ErrorDialog(" Report Name is all ready given !!!\n\n\n Please specify other Name","","Report Name")
                        self.logobj.log_write('SendToServer',LOG_WARNING, ':Report name all ready given DB %s' % (database))
                        self.win.endExecute()
                except Exception,e:
                    import traceback,sys
                    info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                    self.logobj.log_write('ServerParameter', LOG_ERROR, info)
            else:

                id = docinfo.getUserFieldValue(2)
                vId = self.sock.execute(database, uid, self.password, 'ir.values' ,  'search', [('value','=','ir.actions.report.xml,'+str(id))])
                rec = { 'name': self.win.getEditText("txtReportName") }
                res = self.sock.execute(database, uid, self.password, 'ir.values' , 'write',vId,rec)
            oDoc2.store()
            data = read_data_from_file( get_absolute_file_path( oDoc2.getURL()[7:] ) )
            self.getInverseFieldsRecord(0)
            #sock = xmlrpclib.ServerProxy(docinfo.getUserFieldValue(0) +'/xmlrpc/object')

            file_type = oDoc2.getURL()[7:].split(".")[-1]
            res = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'upload_report', int(docinfo.getUserFieldValue(2)),base64.encodestring(data),file_type,{})
            params = {
                'name': self.win.getEditText("txtName"),
                'model': docinfo.getUserFieldValue(3),
                'report_name': self.win.getEditText("txtReportName"),
                'header': (self.win.getCheckBoxState("chkHeader") <> 0),
                'report_type': self.Kind[self.win.getListBoxSelectedItem("lstResourceType")],
            }
            if self.win.getListBoxSelectedItem("lstResourceType")=='OpenOffice':
                params['report_type']=file_type
            res = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'write', int(docinfo.getUserFieldValue(2)), params)
            self.logobj.log_write('SendToServer',LOG_INFO, ':Report %s successfully send using %s'%(params['name'],database))
            self.win.endExecute()
        else:
            ErrorDialog("Either Report Name or Technical Name is blank !!!\nPlease specify appropriate Name","","Blank Field ERROR")
            self.logobj.log_write('SendToServer',LOG_WARNING, ':Either Report Name or Technical Name is blank')
            self.win.endExecute()

    def getID(self):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        params = {
            'name': self.win.getEditText("txtName"),
            'model': docinfo.getUserFieldValue(3),
            'report_name': self.win.getEditText('txtReportName')
        }


        id=self.sock.execute(database, uid, self.password, 'ir.actions.report.xml' ,'create', params)
        return id

    def getInverseFieldsRecord(self,nVal):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        count=0
        oParEnum = doc.getTextFields().createEnumeration()
        while oParEnum.hasMoreElements():
            oPar = oParEnum.nextElement()
            if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
                oPar.SelectedItem = oPar.Items[nVal]
                if nVal==0:
                    oPar.update()

if __name__<>"package" and __name__=="__main__":
    SendtoServer(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( SendtoServer, "org.openoffice.openerp.report.sendtoserver", ("com.sun.star.task.Job",),)


import uno
from com.sun.star.task import XJobExecutor

if __name__<>'package':
    from lib.gui import *

class About(unohelper.Base, XJobExecutor):
    def __init__(self,ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        self.win = DBModalDialog(60, 50, 175, 115, ".:: About OpenERP Report Designer ::.")

        fdBigFont = createUnoStruct("com.sun.star.awt.FontDescriptor")
        fdBigFont.Width = 20
        fdBigFont.Height = 25
        fdBigFont.Weight = 120
        fdBigFont.Family= 3

        oLabelTitle1 = self.win.addFixedText("lblTitle1", 1, 1, 35, 30)
        oLabelTitle1.Model.TextColor = 16056320
        oLabelTitle1.Model.FontDescriptor = fdBigFont
        oLabelTitle1.Model.FontRelief = 1
        oLabelTitle1.Text = "Open"

        oLabelTitle2 = self.win.addFixedText("lblTitle2", 35, 1, 30, 30)
        oLabelTitle2.Model.TextColor = 1
        oLabelTitle2.Model.FontDescriptor = fdBigFont
        oLabelTitle2.Model.FontRelief = 1
        oLabelTitle2.Text = "ERP"

        oLabelProdDesc = self.win.addFixedText("lblProdDesc", 1, 30, 173, 75)
        oLabelProdDesc.Model.TextColor = 1
        fdBigFont.Width = 10
        fdBigFont.Height = 11
        fdBigFont.Weight = 76
        oLabelProdDesc.Model.FontDescriptor = fdBigFont
        oLabelProdDesc.Model.Align = 1
        oLabelProdDesc.Model.FontRelief = 1
        oLabelProdDesc.Model.MultiLine = True
        oLabelProdDesc.Text = "This  package  helps  you  to  create  or  modify\nreports  in  OpenERP.  Once  connected  to  the\nserver, you can design your template of reports\nusing fields  and expressions  and  browsing the\ncomplete structure of OpenERP object database."

        oLabelFooter = self.win.addFixedText("lblFooter", -1, -1, 173, 25)
        oLabelFooter.Model.TextColor = 255
        #oLabelFooter.Model.BackgroundColor = 1
        oLabelFooter.Model.Border = 2
        oLabelFooter.Model.BorderColor = 255
        fdBigFont.Width = 8
        fdBigFont.Height = 9
        fdBigFont.Weight = 100
        oLabelFooter.Model.FontDescriptor = fdBigFont
        oLabelFooter.Model.Align = 1
        oLabelFooter.Model.FontRelief = 1
        oLabelFooter.Model.MultiLine = True
        sMessage = "OpenERP Report Designer v1.0 \nCopyright 2007-TODAY Tiny sprl \nThis product is free software, under the GPL licence."
        oLabelFooter.Text = sMessage

        self.win.doModalDialog("",None)

if __name__<>"package" and __name__=="__main__":
    About(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( About, "org.openoffice.openerp.report.about", ("com.sun.star.task.Job",),)


import uno
import unohelper
import string
import re
import base64

from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from LoginTest import *
    from lib.logreport import *
    from lib.rpc import *
    database="test"
    uid = 1



class ConvertBracesToField( unohelper.Base, XJobExecutor ):

    def __init__(self,ctx):

        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        LoginTest()
        self.logobj=Logger()
        if not loginstatus and __name__=="package":
            exit(1)

        global passwd
        self.password = passwd
        global url
        self.sock=RPCSession(url)
        self.aReportSyntex=[]
        self.getBraces(self.aReportSyntex)

        self.setValue()


    def setValue(self):

        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=  doc.getDocumentInfo()
        count = 0
        regexes = [
            ['[a-zA-Z0-9_]+\.[a-zA-Z0-9_.]+',"Field"],
            ['\\[\\[ *repeatIn\\( *([a-zA-Z0-9_\.]+), *\'([a-zA-Z0-9_]+)\' *\\) *\\]\\]', "RepeatIn"],
            ['\\[\\[ *([a-zA-Z0-9_\.]+) *\\]\\]', "Field"]
            # ['\\[\\[ ([a-zA-Z0-9_]+\.[a-zA-Z1-9]) \\]\\]',"Field"],
            # ['\\[\\[ [a-zA-Z0-9_\.]+ and ([a-zA-Z0-9_\.]+) or .+? \\]\\]',"Field"],
            # ['\\[\\[ ([a-zA-Z0-9_\.]+) or .+? \\]\\]',"Field"],
            # ['\\[\\[ ([a-zA-Z0-9_\.]+) and .+? \\]\\]',"Field"],
            # ['\\[\\[ .+? or ([a-zA-Z0-9_\.]+) \\]\\]',"Field"],
            # ['\\[\\[ (.+?) and ([a-zA-Z0-9_\.]+) \\]\\]',"Field"],
            # ['\\[\\[ .+? % ([a-zA-Z0-9_\.]+) \\]\\]',"Field"]
        ]
        oFieldObject = []
        oRepeatInObjects = []
        saRepeatInList = []
        sHost = docinfo.getUserFieldValue(0)
        nCount = 0
        oParEnum = doc.getTextFields().createEnumeration()
        while oParEnum.hasMoreElements():
            oPar = oParEnum.nextElement()
            nCount += 1
        getList(oRepeatInObjects,sHost,nCount)
        for ro in oRepeatInObjects:
            if ro.find("(")<>-1:
                saRepeatInList.append( [ ro[:ro.find("(")], ro[ro.find("(")+1:ro.find(")")] ])
        try:
            oParEnum = doc.getTextFields().createEnumeration()
            while oParEnum.hasMoreElements():
                oPar = oParEnum.nextElement()
                if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
                    for reg in regexes:
                        res=re.findall(reg[0],oPar.Items[1])
                        if len(res) <> 0:
                            if res[0][0] == "objects":
                                sTemp = docinfo.getUserFieldValue(3)
                                sTemp = "|-." + sTemp[sTemp.rfind(".")+1:] + ".-|"
                                oPar.Items=(sTemp.encode("utf-8"),oPar.Items[1].replace(' ',""))
                                oPar.update()
                            elif type(res[0]) <> type(u''):

                                sObject = self.getRes(self.sock, docinfo.getUserFieldValue(3), res[0][0][res[0][0].find(".")+1:].replace(".","/"))
                                r = self.sock.execute(database, uid, self.password, docinfo.getUserFieldValue(3) , 'fields_get')
                                sExpr="|-." + r[res[0][0][res[0][0].rfind(".")+1:]]["string"] + ".-|"
                                oPar.Items=(sExpr.encode("utf-8"),oPar.Items[1].replace(' ',""))
                                oPar.update()
                            else:

                                obj = None
                                for rl in saRepeatInList:
                                    if rl[0] == res[0][:res[0].find(".")]:
                                        obj=rl[1]
                                try:
                                    sObject = self.getRes(self.sock, obj, res[0][res[0].find(".")+1:].replace(".","/"))
                                    r = self.sock.execute(database, uid, self.password, sObject , 'read',[1])
                                except Exception,e:
                                    r = "TTT"
                                    self.logobj.log_write('ConvertBracesToField', LOG_ERROR, str(e))
                                if len(r) <> 0:
                                    if r <> "TTT":
                                        if len(res)>1:
                                            sExpr=""
                                            print res
                                            if reg[1] == 'Field':
                                                for ires in res:
                                                    try:
                                                        sExpr=r[0][ires[ires.rfind(".")+1:]]
                                                        break
                                                    except Exception,e:
                                                        import traceback,sys
                                                        info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                                                        self.logobj.log_write('ConvertBracesToField', LOG_ERROR,info)
                                                try:
                                                    oPar.Items=(sExpr.encode("utf-8") ,oPar.Items[1])
                                                    oPar.update()
                                                except:
                                                    oPar.Items=(str(sExpr) ,oPar.Items[1])
                                                    oPar.update()
                                                    import traceback,sys
                                                    info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                                                    self.logobj.log_write('ConvertBracesToField', LOG_ERROR, info)

                                        else:
                                            sExpr=r[0][res[0][res[0].rfind(".")+1:]]
                                            try:

                                                if sExpr:
                                                    oPar.Items=(sExpr.encode("utf-8") ,oPar.Items[1])
                                                    oPar.update()
                                                else:
                                                     oPar.Items=(u"/",oPar.Items[1])
                                                     oPar.update()
                                            except:
                                                oPar.Items=(str(sExpr) ,oPar.Items[1])
                                                oPar.update()
                                                import traceback,sys
                                                info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                                                self.logobj.log_write('ConvertBracesToField', LOG_ERROR,info)

                                    else:
                                        oPar.Items=(u""+r,oPar.Items[1])
                                        oPar.update()
                                else:
                                    oPar.Items=(u"TTT",oPar.Items[1])
                                    oPar.update()
        except:
            import traceback,sys
            info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            self.logobj.log_write('ConvertBraceToField', LOG_ERROR, info)

    def getRes(self,sock,sObject,sVar):
        desktop=getDesktop()
        doc =desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        res = sock.execute(database, uid, self.password, sObject , 'fields_get')
        key = res.keys()
        key.sort()
        myval=None
        if not sVar.find("/")==-1:
            myval=sVar[:sVar.find("/")]
        else:
            myval=sVar
        for k in key:
            if (res[k]['type'] in ['many2one']) and k==myval:
                sObject = self.getRes(sock,res[myval]['relation'], sVar[sVar.find("/")+1:])
        return sObject

    def getBraces(self,aReportSyntex=[]):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        aSearchString=[]
        aReplaceString=[]
        aRes=[]

        try:
            regexes = [
                ['\\[\\[ *repeatIn\\( *([a-zA-Z0-9_\.]+), *\'([a-zA-Z0-9_]+)\' *\\) *\\]\\]', "RepeatIn"],
                ['\\[\\[ *([a-zA-Z0-9_\.]+) *\\]\\]', "Field"],
                ['\\[\\[ *.+? *\\]\\]', "Expression"]
            ]

            search = doc.createSearchDescriptor()
            search.SearchRegularExpression = True

            for reg in regexes:
                search.SearchString = reg[0]
                found = doc.findFirst( search )
                while found:
                    res=re.findall(reg[0],found.String)
                    print len(res)

                    if found.String not in [r[0] for r in aReportSyntex] and len(res) == 1 :
                        text=found.getText()
                        oInputList = doc.createInstance("com.sun.star.text.TextField.DropDown")
                        if reg[1]<>"Expression":
                            oInputList.Items=(u""+found.String,u""+found.String)
                        else:
                            oInputList.Items=(u"?",u""+found.String)
                        aReportSyntex.append([oInputList,reg[1]])
                        text.insertTextContent(found,oInputList,False)
                        found.String =""

                    else:
                        aRes.append([res,reg[1]])
                        found = doc.findNext(found.End, search)
            search = doc.createSearchDescriptor()
            search.SearchRegularExpression = False

            for res in aRes:
                for r in res[0]:
                    search.SearchString=r
                    found=doc.findFirst(search)
                    while found:

                        text=found.getText()

                        oInputList = doc.createInstance("com.sun.star.text.TextField.DropDown")
                        if res[1]<>"Expression":
                            oInputList.Items=(u""+found.String,u""+found.String)
                        else:
                            oInputList.Items=(u"?",u""+found.String)
                        aReportSyntex.append([oInputList,res[1]])
                        text.insertTextContent(found,oInputList,False)
                        found.String =""
                        found = doc.findNext(found.End, search)
        except:
            import traceback,sys
            info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            self.logobj.log_write('ConvertBraceToField', LOG_ERROR, info)

if __name__<>"package":
    ConvertBracesToField(None)
else:
    g_ImplementationHelper.addImplementation( ConvertBracesToField, "org.openoffice.openerp.report.convertBF", ("com.sun.star.task.Job",),)

import uno
import unohelper
import string
import re
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from LoginTest import *
    database="test"
    uid = 3

class ConvertFieldsToBraces( unohelper.Base, XJobExecutor ):
    def __init__(self,ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        LoginTest()
        if not loginstatus and __name__=="package":
            exit(1)
        self.aReportSyntex=[]
        self.getFields()

    def getFields(self):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()

        oParEnum = doc.getTextFields().createEnumeration()
        while oParEnum.hasMoreElements():
            oPar = oParEnum.nextElement()
            if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
                oPar.getAnchor().Text.insertString(oPar.getAnchor(),oPar.Items[1],False)
                oPar.dispose()

if __name__<>"package":
    ConvertFieldsToBraces(None)
else:
    g_ImplementationHelper.addImplementation( ConvertFieldsToBraces, "org.openoffice.openerp.report.convertFB", ("com.sun.star.task.Job",),) 

import os
import uno
import unohelper
import string
import tempfile
import base64
import sys

reload(sys)
sys.setdefaultencoding("utf8")
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from LoginTest import *
    from lib.error import *
    from lib.tools import *
    from lib.logreport import *
    from lib.rpc import *
    database="test"
    uid = 3


class ExportToRML( unohelper.Base, XJobExecutor ):
    def __init__(self,ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        LoginTest()
        if not loginstatus and __name__=="package":
            exit(1)

        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        global url
        self.sock=RPCSession(url)

        # Read Data from sxw file
        tmpsxw = tempfile.mktemp('.'+"sxw")

        if not doc.hasLocation():
            mytype = Array(makePropertyValue("MediaType","application/vnd.sun.xml.writer"),)
            doc.storeAsURL("file://"+tmpsxw,mytype)
        data = read_data_from_file( get_absolute_file_path( doc.getURL()[7:] ) )
        file_type = doc.getURL()[7:].split(".")[-1]
        if docinfo.getUserFieldValue(2) == "":
            ErrorDialog("Please Save this file on server","Use Send To Server Option in OpenERP Report Menu","Error")
            exit(1)
    	filename = self.GetAFileName()
    	if not filename:
    	    exit(1)
        global passwd
        self.password = passwd
        try:

            res = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'sxwtorml',base64.encodestring(data),file_type)
            if res['report_rml_content']:
                write_data_to_file( get_absolute_file_path( filename[7:] ), res['report_rml_content'] )
        except Exception,e:
            import traceback,sys
            info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            self.logobj.log_write('ExportToRML',LOG_ERROR, info)
            ErrorDialog("Can't save the file to the hard drive.", "Exception: %s" % e, "Error" )

    def GetAFileName(self):
        sFilePickerArgs = Array(10)
        oFileDialog = createUnoService("com.sun.star.ui.dialogs.FilePicker")
        oFileDialog.initialize(sFilePickerArgs)
        oFileDialog.appendFilter("OpenERP Report File Save To ....","*.rml")

        f_path = "OpenERP-"+ os.path.basename( tempfile.mktemp("","") ) + ".rml"
        initPath = tempfile.gettempdir()
        oUcb = createUnoService("com.sun.star.ucb.SimpleFileAccess")
        if oUcb.exists(initPath):
	    oFileDialog.setDisplayDirectory('file://' + ( os.name == 'nt' and '/' or '' ) + initPath )

        oFileDialog.setDefaultName(f_path )

        sPath = oFileDialog.execute() == 1 and oFileDialog.Files[0] or None
        oFileDialog.dispose()
        return sPath

if __name__<>"package" and __name__=="__main__":
    ExportToRML(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( ExportToRML, "org.openoffice.openerp.report.exporttorml", ("com.sun.star.task.Job",),)

import uno
import string
import unohelper
import xmlrpclib
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from lib.functions import *
    from lib.error import ErrorDialog
    from LoginTest import *
    from lib.rpc import *
    database="test_001"
    uid = 3


class AddLang(unohelper.Base, XJobExecutor ):
    def __init__(self,sVariable="",sFields="",sDisplayName="",bFromModify=False):
        LoginTest()
        if not loginstatus and __name__=="package":
            exit(1)
        global passwd
        self.password = passwd
        self.win = DBModalDialog(60, 50, 180, 225, "Set Lang Builder")

        self.win.addFixedText("lblVariable", 27, 12, 60, 15, "Variable :")
        self.win.addComboBox("cmbVariable", 180-120-2, 10, 120, 15,True,
                            itemListenerProc=self.cmbVariable_selected)
        self.insVariable = self.win.getControl( "cmbVariable" )

        self.win.addFixedText("lblFields", 10, 32, 60, 15, "Variable Fields :")
        self.win.addComboListBox("lstFields", 180-120-2, 30, 120, 150, False,itemListenerProc=self.lstbox_selected)
        self.insField = self.win.getControl( "lstFields" )
        self.win.addFixedText("lblUName", 8, 187, 60, 15, "Displayed name :")
        self.win.addEdit("txtUName", 180-120-2, 185, 120, 15,)

        self.win.addButton('btnOK',-5 ,-5, 45, 15, 'Ok', actionListenerProc = self.btnOk_clicked )
        self.win.addButton('btnCancel',-5 - 45 - 5 ,-5,45,15,'Cancel', actionListenerProc = self.btnCancel_clicked )
        self.sValue=None
        self.sObj=None
        self.aSectionList=[]
        self.sGDisplayName=sDisplayName
        self.aItemList=[]
        self.aComponentAdd=[]
        self.aObjectList=[]
        self.aListFields=[]
        self.aVariableList=[]
        EnumDocument(self.aItemList,self.aComponentAdd)
        desktop=getDesktop()
        doc =desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        self.sMyHost= ""
        global url
        self.sock=RPCSession(url)

        if not docinfo.getUserFieldValue(3) == "" and not docinfo.getUserFieldValue(0)=="":
            self.sMyHost= docinfo.getUserFieldValue(0)
            self.count=0
            oParEnum = doc.getTextFields().createEnumeration()
            while oParEnum.hasMoreElements():
                oPar = oParEnum.nextElement()
                if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
                    self.count += 1
            getList(self.aObjectList, self.sMyHost,self.count)
            cursor = doc.getCurrentController().getViewCursor()
            text=cursor.getText()
            tcur=text.createTextCursorByRange(cursor)

	    self.aVariableList.extend( filter( lambda obj: obj[:obj.find("(")] == "Objects", self.aObjectList ) )

            for i in range(len(self.aItemList)):
		anItem = self.aItemList[i][1]
		component = self.aComponentAdd[i]

                if component == "Document":
		    sLVal = anItem[anItem.find(",'") + 2:anItem.find("')")]
		    self.aVariableList.extend( filter( lambda obj: obj[:obj.find("(")] == sLVal, self.aObjectList ) )

                if tcur.TextSection:
                    getRecersiveSection(tcur.TextSection,self.aSectionList)
                    if component in self.aSectionList:
			sLVal = anItem[anItem.find(",'") + 2:anItem.find("')")]
			self.aVariableList.extend( filter( lambda obj: obj[:obj.find("(")] == sLVal, self.aObjectList ) )

                if tcur.TextTable:
		    if not component == "Document" and component[component.rfind(".") + 1:] == tcur.TextTable.Name:
                        VariableScope(tcur,self.insVariable,self.aObjectList,self.aComponentAdd,self.aItemList,component)

            self.bModify=bFromModify
            if self.bModify==True:
                sItem=""
		for anObject in self.aObjectList:
		    if anObject[:anObject.find("(")] == sVariable:
			sItem = anObject
			self.insVariable.setText( sItem )
		genTree(sItem[sItem.find("(")+1:sItem.find(")")],self.aListFields, self.insField,self.sMyHost,2,ending_excl=['one2many','many2one','many2many','reference'], recur=['many2one'])
                self.sValue= self.win.getListBoxItem("lstFields",self.aListFields.index(sFields))

            for var in self.aVariableList:

		    self.model_ids = self.sock.execute(database, uid, self.password, 'ir.model' ,  'search', [('model','=',var[var.find("(")+1:var.find(")")])])
                    fields=['name','model']
                    self.model_res = self.sock.execute(database, uid, self.password, 'ir.model', 'read', self.model_ids,fields)
                    if self.model_res <> []:
			self.insVariable.addItem(var[:var.find("(")+1] + self.model_res[0]['name'] + ")" ,self.insVariable.getItemCount())
                    else:
                        self.insVariable.addItem(var ,self.insVariable.getItemCount())

            self.win.doModalDialog("lstFields",self.sValue)
        else:
            ErrorDialog("Please insert user define field Field-1 or Field-4","Just go to File->Properties->User Define \nField-1 Eg. http://localhost:8069 \nOR \nField-4 Eg. account.invoice")
            self.win.endExecute()

    def lstbox_selected(self,oItemEvent):
        try:

            desktop=getDesktop()
            doc =desktop.getCurrentComponent()
            docinfo=doc.getDocumentInfo()
            sItem= self.win.getComboBoxText("cmbVariable")
            for var in self.aVariableList:
		if var[:var.find("(")+1]==sItem[:sItem.find("(")+1]:
                    sItem = var
            sMain=self.aListFields[self.win.getListBoxSelectedItemPos("lstFields")]
            t=sMain.rfind('/lang')
            if t!=-1:
		sObject=self.getRes(self.sock,sItem[sItem.find("(")+1:-1],sMain[1:])
                ids = self.sock.execute(database, uid, self.password, sObject ,  'search', [])
                res = self.sock.execute(database, uid, self.password, sObject , 'read',[ids[0]])
		self.win.setEditText("txtUName",res[0][sMain[sMain.rfind("/")+1:]])
            else:
                 ErrorDialog("Please select the Language Field")

        except:
            import traceback;traceback.print_exc()
            self.win.setEditText("txtUName","TTT")
        if self.bModify:
            self.win.setEditText("txtUName",self.sGDisplayName)

    def getRes(self,sock ,sObject,sVar):
        desktop=getDesktop()
        doc =desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        res = sock.execute(database, uid, self.password, sObject , 'fields_get')
        key = res.keys()
        key.sort()
        myval=None
        if not sVar.find("/")==-1:
	    myval=sVar[:sVar.find("/")]
        else:
            myval=sVar
        if myval in key:
            if (res[myval]['type'] in ['many2one']):
                sObject = res[myval]['relation']
		return self.getRes(sock,res[myval]['relation'], sVar[sVar.find("/")+1:])
            else:
                return sObject


    def cmbVariable_selected(self,oItemEvent):
        if self.count > 0 :
            try:
                desktop=getDesktop()
                doc =desktop.getCurrentComponent()
                docinfo=doc.getDocumentInfo()
                self.win.removeListBoxItems("lstFields", 0, self.win.getListBoxItemCount("lstFields"))
                self.aListFields=[]
                tempItem = self.win.getComboBoxText("cmbVariable")
                for var in self.aVariableList:
		    if var[:var.find("(")] == tempItem[:tempItem.find("(")]:
                        sItem=var

		genTree(
		    sItem[ sItem.find("(") + 1:sItem.find(")")],
		    self.aListFields,
		    self.insField,
		    self.sMyHost,
		    2,
		    ending_excl=['one2many','many2one','many2many','reference'],
		    recur=['many2one']
		)

            except:
                import traceback;traceback.print_exc()

    def btnOk_clicked( self, oActionEvent ):
        self.bOkay = True
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        cursor = doc.getCurrentController().getViewCursor()

        itemSelected = self.win.getListBoxSelectedItem( "lstFields" )
        itemSelectedPos = self.win.getListBoxSelectedItemPos( "lstFields" )
        txtUName = self.win.getEditText("txtUName")
        sKey=u""+ txtUName

        if itemSelected != "" and txtUName != "" and self.bModify==True :
            oCurObj=cursor.TextField
            sObjName=self.insVariable.getText()
            sObjName=sObjName[:sObjName.find("(")]
            sValue=u"[[ setLang" + sObjName + self.aListFields[itemSelectedPos].replace("/",".") + ")" " ]]"
            oCurObj.Items = (sKey,sValue)
            oCurObj.update()
            self.win.endExecute()
        elif itemSelected != "" and txtUName != "" :
            oInputList = doc.createInstance("com.sun.star.text.TextField.DropDown")
            sObjName=self.win.getComboBoxText("cmbVariable")
            sObjName=sObjName[:sObjName.find("(")]

            widget = ( cursor.TextTable and cursor.TextTable.getCellByName( cursor.Cell.CellName ) or doc.Text )

            sValue = u"[[setLang" + "(" + sObjName + self.aListFields[itemSelectedPos].replace("/",".") +")" " ]]"
            oInputList.Items = (sKey,sValue)
            widget.insertTextContent(cursor,oInputList,False)

            self.win.endExecute()
        else:
            ErrorDialog("Please Fill appropriate data in Name field \nor select perticular value from the list of fields")

    def btnCancel_clicked( self, oActionEvent ):
        self.win.endExecute()


if __name__<>"package" and __name__=="__main__":
    AddLang()
elif __name__=="package":
    g_ImplementationHelper.addImplementation( AddLang, "org.openoffice.openerp.report.langtag", ("com.sun.star.task.Job",),)

import os
import uno
import unohelper
import xmlrpclib
import base64
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from lib.error import ErrorDialog
    from lib.tools import *
    from LoginTest import *
    from lib.rpc import *
    database="test"
    uid = 3

class AddAttachment(unohelper.Base, XJobExecutor ):
    Kind = {
        'PDF' : 'pdf',
        'OpenOffice': 'sxw',
    }
    def __init__(self,ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        LoginTest()
        if not loginstatus and __name__=="package":
            exit(1)

        self.aSearchResult = []
        desktop=getDesktop()
        oDoc2 = desktop.getCurrentComponent()
        docinfo=oDoc2.getDocumentInfo()

        global passwd
        self.password = passwd
        global url
        self.sock=RPCSession(url)
        if docinfo.getUserFieldValue(2) <> "" and docinfo.getUserFieldValue(3) <> "":
            self.win = DBModalDialog(60, 50, 180, 70, "Add Attachment to Server")
            self.win.addFixedText("lblResourceType", 2 , 5, 100, 10, "Select Appropriate Resource Type:")
            self.win.addComboListBox("lstResourceType", -2, 25, 176, 15,True)
            self.win.addButton('btnOkWithoutInformation', -2 , -5, 25 , 15,'OK' ,actionListenerProc = self.btnOkWithoutInformation_clicked )
        else:
            self.win = DBModalDialog(60, 50, 180, 190, "Add Attachment to Server")
            self.win.addFixedText("lblModuleName",2 , 9, 42, 20, "Select Module:")
            self.win.addComboListBox("lstmodel", -2, 5, 134, 15,True)
            self.lstModel = self.win.getControl( "lstmodel" )
            self.dModel = {}

            # Open a new connexion to the server

            ids = self.sock.execute(database, uid, self.password, 'ir.module.module', 'search', [('name','=','base_report_model'),('state', '=', 'installed')])
            if not len(ids):
                # If the module 'base_report_model' is not installed, use the default model
                self.dModel = {
                    "Partner":'res.partner',
                }
            else:

                ids =self.sock.execute(database, uid, self.password, 'base.report.model' , 'search', [])
                res = self.sock.execute(database, uid, self.password, 'base.report.model' , 'read', ids, ['name','model_id'])
                models = self.sock.execute(database, uid, self.password, 'ir.model' , 'read', map(lambda x:x['model_id'][0], res), ['model'])
                models = dict(map(lambda x:(x['id'],x['model']), models))
                self.dModel = dict(map(lambda x: (x['name'],models[x['model_id'][0]]), res))

            for item in self.dModel.keys():
                self.lstModel.addItem(item, self.lstModel.getItemCount())

            self.win.addFixedText("lblSearchName",2 , 25, 60, 10, "Enter Search String:")
            self.win.addEdit("txtSearchName", 2, 35, 149, 15,)
            self.win.addButton('btnSearch', -2 , 35, 25 , 15,'Search' ,actionListenerProc = self.btnSearch_clicked )

            self.win.addFixedText("lblSearchRecord", 2 , 55, 60, 10, "Search Result:")
            self.win.addComboListBox("lstResource", -2, 65, 176, 70, False )
            self.lstResource = self.win.getControl( "lstResource" )

            self.win.addFixedText("lblResourceType", 2 , 137, 100, 20, "Select Appropriate Resource Type:")
            self.win.addComboListBox("lstResourceType", -2, 147, 176, 15,True )

            self.win.addButton('btnOkWithInformation', -2 , -5, 25 , 15,'OK' ,actionListenerProc = self.btnOkWithInformation_clicked )

        self.lstResourceType = self.win.getControl( "lstResourceType" )
        for kind in self.Kind.keys():
            self.lstResourceType.addItem( kind, self.lstResourceType.getItemCount() )

        self.win.addButton('btnCancel', -2 - 27 , -5 , 30 , 15, 'Cancel' ,actionListenerProc = self.btnCancel_clicked )
        self.win.doModalDialog("lstResourceType", self.Kind.keys()[0])

    def btnSearch_clicked( self, oActionEvent ):
        modelSelectedItem = self.win.getListBoxSelectedItem("lstmodel")
        if modelSelectedItem == "":
            return

        desktop=getDesktop()
        oDoc2 = desktop.getCurrentComponent()
        docinfo=oDoc2.getDocumentInfo()


        self.aSearchResult =self.sock.execute( database, uid, self.password, self.dModel[modelSelectedItem], 'name_search', self.win.getEditText("txtSearchName"))
        self.win.removeListBoxItems("lstResource", 0, self.win.getListBoxItemCount("lstResource"))
        if self.aSearchResult == []:
            ErrorDialog("No search result found !!!", "", "Search ERROR" )
            return

        for result in self.aSearchResult:
            self.lstResource.addItem(result[1],result[0])

    def _send_attachment( self, name, data, res_model, res_id ):
        desktop = getDesktop()
        oDoc2 = desktop.getCurrentComponent()
        docinfo = oDoc2.getDocumentInfo()

        params = {
            'name': name,
            'datas': base64.encodestring( data ),
            'datas_fname': name,
            'res_model' : res_model,
            'res_id' : int(res_id),
        }

        return self.sock.execute( database, uid, self.password, 'ir.attachment', 'create', params )

    def send_attachment( self, model, resource_id ):
        desktop = getDesktop()
        oDoc2 = desktop.getCurrentComponent()
        docinfo = oDoc2.getDocumentInfo()

        if oDoc2.getURL() == "":
            ErrorDialog("Please save your file", "", "Saving ERROR" )
            return None

        url = oDoc2.getURL()
        if self.Kind[self.win.getListBoxSelectedItem("lstResourceType")] == "pdf":
            url = self.doc2pdf(url[7:])

        if url == None:
            ErrorDialog( "Ploblem in creating PDF", "", "PDF Error" )
            return None

        url = url[7:]
        data = read_data_from_file( get_absolute_file_path( url ) )
        return self._send_attachment( os.path.basename( url ), data, model, resource_id )

    def btnOkWithoutInformation_clicked( self, oActionEvent ):
        desktop = getDesktop()
        oDoc2 = desktop.getCurrentComponent()
        docinfo = oDoc2.getDocumentInfo()

        if self.win.getListBoxSelectedItem("lstResourceType") == "":
            ErrorDialog("Please select resource type", "", "Selection ERROR" )
            return

        res = self.send_attachment( docinfo.getUserFieldValue(3), docinfo.getUserFieldValue(2) )
        self.win.endExecute()

    def btnOkWithInformation_clicked(self,oActionEvent):
        if self.win.getListBoxSelectedItem("lstResourceType") == "":
            ErrorDialog( "Please select resource type", "", "Selection ERROR" )
            return

        if self.win.getListBoxSelectedItem("lstResource") == "" or self.win.getListBoxSelectedItem("lstmodel") == "":
            ErrorDialog("Please select Model and Resource","","Selection ERROR")
            return

        resourceid = None
        for s in self.aSearchResult:
            if s[1] == self.win.getListBoxSelectedItem("lstResource"):
                resourceid = s[0]
                break

        if resourceid == None:
            ErrorDialog("No resource selected !!!", "", "Resource ERROR" )
            return

        res = self.send_attachment( self.dModel[self.win.getListBoxSelectedItem('lstmodel')], resourceid )
        self.win.endExecute()

    def btnCancel_clicked( self, oActionEvent ):
        self.win.endExecute()

    def doc2pdf(self, strFile):
        oDoc = None
        strFilterSubName = ''

        strUrl = convertToURL( strFile )
        desktop = getDesktop()
        oDoc = desktop.loadComponentFromURL( strUrl, "_blank", 0, Array(self._MakePropertyValue("Hidden",True)))
        if oDoc:
            strFilterSubName = ""
            # select appropriate filter
            if oDoc.supportsService("com.sun.star.presentation.PresentationDocument"):
                strFilterSubName = "impress_pdf_Export"
            elif oDoc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
                strFilterSubName = "calc_pdf_Export"
            elif oDoc.supportsService("com.sun.star.text.WebDocument"):
                strFilterSubName = "writer_web_pdf_Export"
            elif oDoc.supportsService("com.sun.star.text.GlobalDocument"):
                strFilterSubName = "writer_globaldocument_pdf_Export"
            elif oDoc.supportsService("com.sun.star.text.TextDocument"):
                strFilterSubName = "writer_pdf_Export"
            elif oDoc.supportsService("com.sun.star.drawing.DrawingDocument"):
                strFilterSubName = "draw_pdf_Export"
            elif oDoc.supportsService("com.sun.star.formula.FormulaProperties"):
                strFilterSubName = "math_pdf_Export"
            elif oDoc.supportsService("com.sun.star.chart.ChartDocument"):
                strFilterSubName = "chart_pdf_Export"
            else:
                pass

            filename = len(strFilterSubName) > 0 and convertToURL( os.path.splitext( strFile )[0] + ".pdf" ) or None

            if len(strFilterSubName) > 0:
                oDoc.storeToURL( filename, Array(self._MakePropertyValue("FilterName", strFilterSubName ),self._MakePropertyValue("CompressMode", "1" )))

            oDoc.close(True)
            # Can be None if len(strFilterSubName) <= 0
            return filename

    def _MakePropertyValue(self, cName = "", uValue = u"" ):
       oPropertyValue = createUnoStruct( "com.sun.star.beans.PropertyValue" )
       if cName:
          oPropertyValue.Name = cName
       if uValue:
          oPropertyValue.Value = uValue
       return oPropertyValue


if __name__<>"package" and __name__=="__main__":
    AddAttachment(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( AddAttachment, "org.openoffice.openerp.report.addattachment", ("com.sun.star.task.Job",),)
