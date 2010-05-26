import uno
import xmlrpclib
import re
import socket
import cPickle
import marshal
import tempfile
if __name__<>"package":
    from gui import *
    database="test"
    uid = 3

def genTree(object,aList,insField,host,level=3, ending=[], ending_excl=[], recur=[], root='', actualroot=""):
    try:
        sock = xmlrpclib.ServerProxy(host+'/xmlrpc/object')
        desktop=getDesktop()
        doc =desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        res = sock.execute(database, uid, docinfo.getUserFieldValue(1), object , 'fields_get')
        key = res.keys()
        key.sort()
        for k in key:
            if (not ending or res[k]['type'] in ending) and ((not ending_excl) or not (res[k]['type'] in ending_excl)):
                insField.addItem(root+'/'+res[k]["string"],len(aList))
                aList.append(actualroot+'/'+k)
            if (res[k]['type'] in recur) and (level>0):
                genTree(res[k]['relation'],aList,insField,host ,level-1, ending, ending_excl, recur,root+'/'+res[k]["string"],actualroot+'/'+k)
    except:
        import traceback;traceback.print_exc()

def VariableScope(oTcur,insVariable,aObjectList,aComponentAdd,aItemList,sTableName=""):
    if sTableName.find(".") != -1:
        print sTableName,1
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
                        print aObjectList[j]
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
            aObjectList.append("List of " + docinfo.getUserFieldValue(3))
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
				getRelation(docinfo.getUserFieldValue(3), sPath[sPath.find(".")+1:], sItem[sItem.find(",'")+2:sItem.find("')")],aObjectList,host)
    else:
        aObjectList.append("List of " + docinfo.getUserFieldValue(3))

def getRelation(sRelName, sItem, sObjName, aObjectList, host ):
        sock = xmlrpclib.ServerProxy(host+'/xmlrpc/object')
        desktop=getDesktop()
        doc =desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        res = sock.execute(database, uid, docinfo.getUserFieldValue(1), sRelName , 'fields_get')
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
        sItem=oPar.Items[1]
	if sItem[sItem.find("[[ ")+3:sItem.find("(")]=="repeatIn" and not oPar.Items in aItemList:
	    aItemList.append( oPar.Items )
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
                        print 2
                        getChildTable(oCur,aItemList,aComponentAdd,oPar.Name)
                    else:
                        print 1
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
                import traceback;traceback.print_exc()
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
def getConnectionStatus(url):
    m = re.match('^(http[s]?://|socket://)([\w.\-]+):(\d{1,5})$', url or '')
    if not m:
        return -1
    if m.group(1) == 'http://' or m.group(1) == 'https://':
        sock = xmlrpclib.ServerProxy(url + '/xmlrpc/db')
        try:
            return sock.list()
        except:
            return -1
    else:
        sock = mysocket
        #sock = xmlrpclib.ServerProxy(url + '/xmlrpc/common')
        try:
            sock.connect(m.group(2), int(m.group(3)))
            sock.mysend(('db', 'list'))
            res = sock.myreceive()
            sock.disconnect()
            return res
        except Exception, e:
            return -1

class Myexception(Exception):
    def __init__(self, faultCode, faultString):
        self.faultCode = faultCode
        self.faultString = faultString

class mysocket:
    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
        self.sock.settimeout(60)
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
        res = cPickle.loads(msg)
        if isinstance(res[0],Exception):
            if exception:
                raise Myexception(str(res[0]), str(res[1]))
            raise res[0]
        else:
            return res[0]

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


