##########################################################################
#
# Portions of this file are under the following copyright and license:
#
#
#   Copyright (c) 2003-2004 Danny Brewer 
#   d29583@groovegarden.com 
# 
#   This library is free software; you can redistribute it and/or 
#   modify it under the terms of the GNU Lesser General Public 
#   License as published by the Free Software Foundation; either 
#   version 2.1 of the License, or (at your option) any later version. 
# 
#   This library is distributed in the hope that it will be useful, 
#   but WITHOUT ANY WARRANTY; without even the implied warranty of 
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU 
#   Lesser General Public License for more details. 
# 
#   You should have received a copy of the GNU Lesser General Public 
#   License along with this library; if not, write to the Free Software 
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA 
# 
#   See:  http://www.gnu.org/licenses/lgpl.html 
#
# 
# and other portions are under the following copyright and license:
#
#
#    OpenERP, Open Source Management Solution>..
#    Copyright (C) 2004-2010 OpenERP SA (<http://openerp.com>). 
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
##############################################################################

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

def genTree(object, aList, insField, host, level=3, ending=None, ending_excl=None, recur=None, root='', actualroot=""):
    if ending is None:
        ending = []
    if ending_excl is None:
        ending_excl = []
    if recur is None:
        recur = []
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

def VariableScope(oTcur, insVariable, aObjectList, aComponentAdd, aItemList, sTableName=""):
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

def getList(aObjectList, host, count):
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

def getRelation(sRelName, sItem, sObjName, aObjectList, host):
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


def getPath(sPath, sMain):
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

def EnumDocument(aItemList, aComponentAdd):
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

def getChildTable(oPar, aItemList, aComponentAdd, sTableName=""):
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

def getRecersiveSection(oCurrentSection, aSectionList):
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



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
