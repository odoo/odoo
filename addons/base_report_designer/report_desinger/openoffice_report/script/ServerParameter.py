import uno
import string
import unohelper
import xmlrpclib
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from lib.error import ErrorDialog
    from lib.functions import *
    from Change import *
    database="test"

class ServerParameter( unohelper.Base, XJobExecutor ):
    def __init__(self,ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        self.win=DBModalDialog(60, 50, 160, 108, "Server Connection Parameter")

        self.win.addFixedText("lblVariable", 2, 12, 35, 15, "Server URL")
        if docinfo.getUserFieldValue(0)=="":
            docinfo.setUserFieldValue(0,"http://localhost:8069")
        self.win.addEdit("txtHost",-34,9,91,15,docinfo.getUserFieldValue(0))
        self.win.addButton('btnChange',-2 ,9,30,15,'Change' ,actionListenerProc = self.btnChange_clicked )

        self.win.addFixedText("lblDatabaseName", 6, 31, 31, 15, "Database")
        #self.win.addFixedText("lblMsg", -2,28,123,15)
        self.win.addComboListBox("lstDatabase", -2,28,123,15, True)
        self.lstDatabase = self.win.getControl( "lstDatabase" )
        #self.win.selectListBoxItem( "lstDatabase", docinfo.getUserFieldValue(2), True )
        #self.win.setEnabled("lblMsg",False)

        self.win.addFixedText("lblLoginName", 17, 51, 20, 15, "Login")
        self.win.addEdit("txtLoginName",-2,48,123,15,docinfo.getUserFieldValue(1))

        self.win.addFixedText("lblPassword", 6, 70, 31, 15, "Password")
        self.win.addEdit("txtPassword",-2,67,123,15,)
        self.win.setEchoChar("txtPassword",42)


        self.win.addButton('btnOK',-2 ,-5, 60,15,'Connect', actionListenerProc = self.btnOk_clicked )

        self.win.addButton('btnCancel',-2 - 60 - 5 ,-5, 35,15,'Cancel', actionListenerProc = self.btnCancel_clicked )
        sValue=""
        if docinfo.getUserFieldValue(0)<>"":
            res=getConnectionStatus(docinfo.getUserFieldValue(0))
            if res == -1:
                sValue="Could not connect to the server!"
                self.lstDatabase.addItem("Could not connect to the server!",0)
            elif res == 0:
                sValue="No Database found !!!"
                self.lstDatabase.addItem("No Database found !!!",0)
            else:
                self.win.removeListBoxItems("lstDatabase", 0, self.win.getListBoxItemCount("lstDatabase"))
                for i in range(len(res)):
                    self.lstDatabase.addItem(res[i],i)
                sValue = database

        self.win.doModalDialog("lstDatabase",sValue)

        #self.win.doModalDialog("lstDatabase",docinfo.getUserFieldValue(2))

    def btnOk_clicked(self,oActionEvent):
        sock = xmlrpclib.ServerProxy(self.win.getEditText("txtHost")+'/xmlrpc/common')
        sDatabase=self.win.getListBoxSelectedItem("lstDatabase")
        sLogin=self.win.getEditText("txtLoginName")
        sPassword=self.win.getEditText("txtPassword")
        UID = sock.login(sDatabase,sLogin,sPassword)
        if not UID:
            ErrorDialog("Connection Refuse...","Please enter valid Login/Password")
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
            ErrorDialog(" You can start creating your report in \nthe current document.","Take care to save it as a .SXW file \nbefore sending to the server.","Message")
            self.win.endExecute()

    def btnCancel_clicked(self, oActionEvent ):
        self.win.endExecute()

    def btnChange_clicked(self,oActionEvent):
        try:
            aVal=[]
            url= self.win.getEditText("txtHost")
            Change(aVal,url)
            if aVal[1]== -1:
                ErrorDialog(aVal[0],"")
            elif aVal[1]==0:
                ErrorDialog(aVal[0],"")
            else:
                self.win.setEditText("txtHost",aVal[0])
                self.win.removeListBoxItems("lstDatabase", 0, self.win.getListBoxItemCount("lstDatabase"))
                for i in range(len(aVal[1])):
                    self.lstDatabase.addItem(aVal[1][i],i)
        except Exception, e:
            print "Exception: %s\n", repr(e)


if __name__<>"package" and __name__=="__main__":
    ServerParameter(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( ServerParameter, "org.openoffice.openerp.report.serverparam", ("com.sun.star.task.Job",),)

