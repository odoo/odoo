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
using System.Drawing.Imaging;
using System.IO;
using System.Windows.Forms;
using System.Text.RegularExpressions;
using OpenERPClient;

namespace OpenERPOutlookPlugin
{
    public class ConfigManager
    {
        string openerp_config_file = "openerp_config.ini";

        public void SaveConfigurationSetting()
        {
            string filepath = Tools.GetAppFolderPath();
            OpenERPOutlookPlugin openerp_outlook = Cache.OpenERPOutlookPlugin;
            OpenERPConnect openerp_connect = openerp_outlook.Connection;
            filepath = Path.Combine(filepath, openerp_config_file);
            string[] datas = { "url=" + openerp_connect.URL, "userid=" + openerp_connect.UserId, "dbname=" + openerp_connect.DBName,"rempwd="+openerp_connect.rempwd,"pswrd=" + openerp_connect.pswrd };
            StreamWriter userfile = new StreamWriter(filepath, false);

            foreach (string data in datas)
            {
                userfile.WriteLine(data);
            }
            userfile.Close();

        }
        public void LoadConfigurationSetting()
        {

            string filePath = Tools.GetAppFolderPath();
            filePath = Path.Combine(filePath, this.openerp_config_file);
            OpenERPConnect openerp_connect=null;
            OpenERPOutlookPlugin openerp_outlook=null;
            openerp_outlook = Cache.OpenERPOutlookPlugin;
            if (openerp_outlook == null)
            {

                openerp_outlook = new OpenERPOutlookPlugin(openerp_connect);
            }
                openerp_connect = openerp_outlook.Connection;
                if (openerp_connect == null)
            {
               openerp_connect = new OpenERPConnect();
            }
            
            if (File.Exists(filePath))
            {

                string line;

                using (StreamReader file = new StreamReader(filePath))
                {
                    while ((line = file.ReadLine()) != null)
                    {
                        char[] delimiters = new char[] { '=' };
                        string[] parts = line.Split(delimiters, 2);

                        for (int i = 0; i < parts.Length; i += 2)
                        {
                            if (parts[i] == "url")
                                openerp_connect.URL = parts[i + 1].Trim();
                            else if (parts[i] == "userid")
                                openerp_connect.UserId = parts[i + 1].Trim();
                            else if (parts[i] == "dbname")
                                openerp_connect.DBName = parts[i + 1].Trim();                          
                            else if (parts[i] == "pswrd")
                                openerp_connect.pswrd = parts[i + 1].Trim();
                            else if (parts[i] == "rempwd")
                            {
                                openerp_connect.rempwd = false;
                                if (parts[i + 1].Trim().ToLower() == "true")
                                    openerp_connect.rempwd = true;
                            }

                        }
                    }
                    file.Close();
                }
            }
            openerp_outlook.Connection = openerp_connect;
            Cache.OpenERPOutlookPlugin = openerp_outlook;
        }        

    }
}
