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
using System.Drawing;
using System.Windows.Forms;
using System.Diagnostics;
using OpenERPClient;

namespace OpenERPOutlookPlugin
{


    public partial class frm_openerp_configuration : Form
    {
        public string combodb_val;
        public string url;
        private ConfigManager config_manager;
        
        public frm_openerp_configuration()
        {
            InitializeComponent();

        }            
            
        void load_dbname_list()
        {            
            combo_config_database.Items.Clear();            
            OpenERPOutlookPlugin openerp_outlook = Cache.OpenERPOutlookPlugin;
            OpenERPConnect openerp_connect = openerp_outlook.Connection;
            try
            {
                if (openerp_connect.URL != null && openerp_connect.URL != "")
                {
                    object[] res_dblist = openerp_connect.DBList();
                    foreach (var selection in res_dblist)
                    {
                        combo_config_database.Items.Add(selection);
                    }
                }
            }
            catch
            {
                this.setdblist(openerp_connect.DBName);
            }
        }
        public void setdblist(string dbname)
        {
            txt_dbname.Visible = true;
            txt_dbname.Text = dbname;
            combo_config_database.Visible = false;
        }
        private void frm_openerp_configuration_Load(object sender, EventArgs e)
        {
            try
            {
                this.config_manager = new ConfigManager();
                this.config_manager.LoadConfigurationSetting();
                

                OpenERPOutlookPlugin openerp_outlook = Cache.OpenERPOutlookPlugin;
                OpenERPConnect openerp_connect = openerp_outlook.Connection;
                if (this.txt_server_config.Text != "")
                {
                    openerp_connect.URL = this.txt_server_config.Text;
                }
                if (openerp_connect.rempwd == true)
                {
                    this.txt_password.Text = Tools.DecryptB64Pwd(openerp_connect.pswrd);
                    this.chkpwd.Checked = true;
                }
                if (openerp_connect.URL != null)
                {
                    this.txt_server_config.Text = openerp_connect.URL;
                    this.txt_username.Text = openerp_connect.UserId;                                        
                    try
                    {
                        object[] res_dblist = openerp_connect.DBList();
                        foreach (string selection in res_dblist)
                        {
                            if (openerp_connect.DBName != "" && selection == openerp_connect.DBName)
                                this.combo_config_database.SelectedText = openerp_connect.DBName;

                        }
                        this.load_dbname_list();
                    }
                    catch
                    {
                        this.setdblist(openerp_connect.DBName);
                    }
                 
                }
                
                
            }
            catch(Exception ex)
            {
                Connect.handleException(ex);
            }

        }       

        private void btn_main_close_Click(object sender, EventArgs e)
        {
            this.Close();
        }

        private void btn_openerp_connect_Click(object sender, EventArgs e)
        {

            try
            {
                url = txt_server_config.Text;
                string dbname;
                if (txt_dbname.Visible == true)
                {
                    dbname = txt_dbname.Text;
                }
                else
                {
                    dbname = combo_config_database.Text;
                }
                OpenERPOutlookPlugin openerp_outlook = Cache.OpenERPOutlookPlugin;
                OpenERPConnect openerp_connect = openerp_outlook.Connection;
                openerp_connect.URL = url;
                openerp_connect.DBName = dbname;
                openerp_connect.UserId = txt_username.Text;               
                openerp_connect.rempwd = chkpwd.Checked;
                if (chkpwd.Checked)
                {
                    openerp_connect.pswrd = Tools.EncryptB64Pwd(txt_password.Text);
                }
                else
                    openerp_connect.pswrd = "";
                if (openerp_connect.Login(openerp_connect.DBName, openerp_connect.UserId, txt_password.Text) != 0)
                {
                    openerp_outlook.Connection = openerp_connect;
                    Cache.OpenERPOutlookPlugin = openerp_outlook;
                    this.config_manager.SaveConfigurationSetting();
                    
                    Connect.displayMessage("Successfully login to OpenERP.");                    
                    this.Close();
                }

            }
            catch (Exception)
            {
                MessageBox.Show("Authentication Error!\nInvalid Database.", Form.ActiveForm.Text, MessageBoxButtons.OK, MessageBoxIcon.Information);
            }

        }

        private void btn_open_server_url_form_Click(object sender, EventArgs e)
        {
            frm_openerp_connection openerp_connection = new frm_openerp_connection(this.txt_server_config);

            openerp_connection.Show();

        }        

        private void txt_server_config_TextChanged(object sender, EventArgs e)
        {
            try
            {
                OpenERPOutlookPlugin openerp_outlook = Cache.OpenERPOutlookPlugin;
                OpenERPConnect openerp_connect = openerp_outlook.Connection;
                openerp_connect.URL = txt_server_config.Text;
                this.combo_config_database.Text = "";
                this.txt_dbname.Text = "";
                try
                {
                    openerp_connect.DBList();
                    this.load_dbname_list();
                    if (txt_dbname.Visible)
                        txt_dbname.Visible = false;
                    combo_config_database.Visible = true;
                }
                catch
                {
                    if (combo_config_database.Visible)
                        combo_config_database.Visible = false;
                    this.txt_dbname.Visible = true;
                }        
                this.txt_username.Text = "";
                this.txt_password.Text = "";                
            }
            catch (Exception ex)
            {
                Connect.handleException(ex);
            }
        }

        private void richTextBox1_LinkClicked(object sender, LinkClickedEventArgs e)
        {
            System.Diagnostics.Process.Start("http://www.openerp.com",e.LinkText);
        }       
    }

}

