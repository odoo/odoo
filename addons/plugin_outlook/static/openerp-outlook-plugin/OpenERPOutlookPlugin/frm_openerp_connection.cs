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
using System.Windows.Forms;
using OpenERPClient;

namespace OpenERPOutlookPlugin
{
    public partial class frm_openerp_connection : Form
    {
        TextBox txtServerURL;
        public frm_openerp_connection()
        {
            InitializeComponent();            
        }
        public frm_openerp_connection(TextBox txt)
        {
            InitializeComponent();
            this.txtServerURL = txt;
        }

        private void frm_openerp_connection_Load(object sender, EventArgs e)
        {
            if (this.txtServerURL.Text != "")
            {
                string[] url = Tools.SplitURL(this.txtServerURL.Text);
                this.txt_server_port.Text = url[2];
                this.txt_server_host.Text = url[1];
                if (url[0] == "https")
                    this.chkSSL.Checked = true;
                else
                    this.chkSSL.Checked = false;
            }
        }


        private void btn_server_ok_Click(object sender, EventArgs e)
        {
            try
            {
                OpenERPOutlookPlugin openerp_outlook = Cache.OpenERPOutlookPlugin;
                OpenERPConnect openerp_connect = openerp_outlook.Connection;
                string url = Tools.JoinURL(this.txt_server_host.Text, this.txt_server_port.Text, this.chkSSL.Checked);
                this.txtServerURL.Text = url;
                openerp_connect.check_connectivity();
                this.Close();
            }
            catch (Exception ex)
            {
                Connect.handleException(ex);
            }
        }

        private void btn_server_close_Click(object sender, EventArgs e)
        {

            this.Close();
        }


    }
}
