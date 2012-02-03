/*
    OpenERP, Open Source Business Applications
    Copyright (c) 2011 OpenERP S.A. <http://openerp.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/


using System;
using System.Collections;
using System.Drawing;
using System.IO;
using outlook = Microsoft.Office.Interop.Outlook;


namespace OpenERPOutlookPlugin
{
    static public class Tools
    {
        static public outlook.MailItem[] MailItems()
        {
            Microsoft.Office.Interop.Outlook.Application app = null;
            app = new Microsoft.Office.Interop.Outlook.Application();
            ArrayList mailItems = new ArrayList();
            foreach (var selection in app.ActiveExplorer().Selection)
            {
                if (selection is outlook.MailItem)
                {
                    mailItems.Add((outlook.MailItem)selection);
                }
            }
            return (outlook.MailItem[])mailItems.ToArray(typeof(outlook.MailItem));
        }
        
        static public string[] SplitURL(string url)
        {
            /*
             
             * Split the url in three parts protocal host and port number.
               :Param string url : url to split.
             * returnts the string array which contains the protocol, host name and port number.
             
             */
            string protocall = "";
            string host = "localhost";
            string port = "8069";
            if (url != "")
            {
                string[] server = url.Split("://".ToCharArray());
                protocall = server[0];

                host = server[3];
                port = "";
                if (server.Length > 4) port = server[4];
            }
            return new string[] { protocall, host, port };

        }
        static public string JoinURL(string host, string port, bool ssl)
        {
            /*
             
             * Join the url as per the host, port and protocols are given.
               :Param string host : host name  
               :Param string port : port number 
               :Param boolean ssl : protocol
             * reruns a string url combination of host, port and protocol.
             
             */
            string protocall = "http";
            if (ssl) protocall = "https";
            string url = protocall + "://" + host;
            if (port != "") url += ":" + port;
            return url;
        }
        static public Hashtable GetAttachments(outlook.MailItem mail)
        {
            /*
             
             * Gets the attachments of selected mail of outlook mail items.
               :Param outlook.MailItem mail : gives the selected mail item from the outlook.
             * returns the hashtable (dictionary) value of the attachemts.
             */
            System.IO.FileStream inFile;
            Hashtable attach = new Hashtable();
            string[] strattch = new string[4];
            foreach (outlook.Attachment attach1 in mail.Attachments)
            {
                string filename = Tools.GetAppFolderPath() + attach1.FileName;
                attach1.SaveAsFile(filename);
                inFile = new System.IO.FileStream(filename, System.IO.FileMode.Open, System.IO.FileAccess.Read);
                byte[] datas = new Byte[inFile.Length];
                long bytesRead = inFile.Read(datas, 0, (int)inFile.Length);
                inFile.Close();
                string fdata = System.Convert.ToBase64String(datas);
                attach.Add(attach1.FileName, fdata);
                strattch[0] = attach1.FileName;
                System.IO.File.Delete(filename);
            }
            return attach;
        }
        static public string GetAppFolderPath()
        {
            /*
             
             * Gets the path of Applicaion folder.
             * returns String value of file path.
              
            */
            string filePath = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            filePath = System.IO.Path.Combine(filePath, "OpenERPOutlook");
            if (!Directory.Exists(filePath))
            {
                Directory.CreateDirectory(filePath);
            }
            return filePath;
        }        

        static public string GetMessageId(outlook.MailItem mail)
        {
            var propertyAccessor = mail.PropertyAccessor;
            string message_id = propertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x1035001E").ToString();
            return message_id;
        }
        static public string GetHeader(outlook.MailItem mail)
        {
            var propertyAccessor = mail.PropertyAccessor;
            //string HEADERS = propertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/string/{3f0a69e0-7f56-11d2-b536-00aa00bbb6e6}/urn:schemas:httpmail:content-disposition-type").ToString(); 
            string HEADERS = propertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x007D001E").ToString();
            return HEADERS;

        }
      
        static public string EncryptB64Pwd(string pwd)
        {
            /*
             
             * Accepts the string password and encrypt it into the base64 format.
               :Param string pwd : A normal string Password.
             * returns the encrypted base64 passwod from the normal string value.
             
             */
            byte[] encbuff = System.Text.Encoding.UTF8.GetBytes(pwd);
            string encodepwd = Convert.ToBase64String(encbuff);
            return "[" + encodepwd + "]";

        }
        static public string DecryptB64Pwd(string pwd)
        {
            /*
             
             * Accept the base64 fromat string value and decrypt it to normal string. 
               :Param : string pwd : A base64 value password.
             * returns the decrypted string value from the base64 value.
             */
            string pswd = pwd.Substring(1, (pwd.Length - 2));
            byte[] decbuff = Convert.FromBase64String(pswd);
            string decodpwd = System.Text.Encoding.UTF8.GetString(decbuff);
            return decodpwd;
        }
    }
}
