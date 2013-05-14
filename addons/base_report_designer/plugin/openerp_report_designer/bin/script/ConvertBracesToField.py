#########################################################################
#
#  Copyright (c) 2003-2004 Danny Brewer d29583@groovegarden.com
#  Copyright (C) 2004-2010 OpenERP SA (<http://openerp.com>).
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2.1 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-13017 USA
#
#  See:  http://www.gnu.org/licenses/lgpl.html
#
#############################################################################

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

    def __init__(self, ctx):

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

    def getRes(self, sock, sObject, sVar):
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

    def getBraces(self, aReportSyntex=None):
        if aReportSyntex is None:
            aReportSyntex = []
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


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
