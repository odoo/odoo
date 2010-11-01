##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

 #!/usr/bin/python
 #-*- encoding: utf-8 -*-

import sys
import chilkat
import os
from manager import ustr
import win32ui
import email
cemail = chilkat.CkEmail()
dt = chilkat.SYSTEMTIME()
def generateEML(mail):
    sub = (mail.Subject).replace(' ','')
    body = mail.Body.encode("utf-8")
    recipients = mail.Recipients
    sender_email = mail.SenderEmailAddress
    sender_name = mail.SenderEmailAddress
    attachments=mail.Attachments

    cemail = chilkat.CkEmail()
    cemail.put_Subject (ustr(sub).encode('iso-8859-1'))
    cemail.put_Body (ustr(body).encode('utf-8'))
    cemail.put_FromAddress (ustr(sender_email).encode('iso-8859-1'))
    cemail.put_From (ustr(sender_email).encode('iso-8859-1'))

    for i in xrange(1, recipients.Count+1):
        name = ustr(recipients.Item(i).Name).encode('iso-8859-1')
        address = ustr(recipients.Item(i).Address).encode('iso-8859-1')
        cemail.AddTo(name,address)

    eml_name= ustr(sub).encode('iso-8859-1')+'-'+str(mail.EntryID)[-9:]
    ls = ['*', '/', '\\', '<', '>', ':', '?', '"', '|', '\t', '\n']
    #mails_folder_path = os.path.abspath("%temp%\\dialogs\\resources\\mails\\")
    mails_folder_path = os.path.abspath("C:\\printing")
    attachments_folder_path = mails_folder_path + "\\attachments\\"
    if not os.path.exists(attachments_folder_path):
        os.makedirs(attachments_folder_path)
    for i in xrange(1, attachments.Count+1):
        fn = eml_name + '-' + ustr(attachments[i].FileName).encode('iso-8859-1')
        for c in ls:
            fn = fn.replace(c,'')
        if len(fn) > 64:
            l = 64 - len(fn)
            f = fn.split('-')
            fn = '-'.join(f[1:])
            if len(fn) > 64:
                l = 64 - len(fn)
                f = fn.split('.')
                fn = f[0][0:l] + '.' + f[-1]
        att_file = os.path.join(attachments_folder_path, fn)
        if os.path.exists(att_file):
            os.remove(att_file)
        f1  = att_file
        attachments[i].SaveAsFile(att_file)
        contentType = cemail.addFileAttachment(att_file)
        if (contentType == None ):
            print mail.lastErrorText()
            sys.exit()


    if not os.path.exists(mails_folder_path):
        os.makedirs(mails_folder_path)
    for c in ls:
        eml_name = eml_name.replace(c,'')
    if len(eml_name) > 64:
       l = 64 - len(eml_name)
       f = eml_name.split('-')
       eml_name = f[0][0:l] + '.' + f[-1]
    eml_path = ustr(os.path.join(mails_folder_path,eml_name+".eml")).encode('iso-8859-1')
    success = cemail.SaveEml(eml_path)
    fp = open(eml_path, 'rb')
    new_mail = email.message_from_file(fp)
    fp.close()
    if (success == False):
        print cemail.lastErrorText()
        sys.exit()
    return new_mail