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
using System.Windows.Forms;
using OpenERPClient;

namespace OpenERPOutlookPlugin
{
    public partial class frm_contact : Form
    {

        public frm_contact()
        {
            InitializeComponent();
        }

        public frm_contact(string contact_name, string email_id)
        {
            InitializeComponent();
            txt_contactname_create_contact.Text = contact_name;
            txtemail.Text = email_id;

        }
      
        private void btncancel_Click(object sender, EventArgs e)
        {
            this.Close();
        }

        private void btnCreate_partner_Click(object sender, EventArgs e)
        {

            try
            {
                Cache.OpenERPOutlookPlugin.CreateContactRecord(0, txt_contactname_create_contact.Text, txtemail.Text);
                this.Close();
            }
            catch (Exception ex)
            {
                Connect.handleException(ex);
            }
        }

        private void btnCancel_Click(object sender, EventArgs e)
        {
            this.Close();
        }

        private void btnLink_partner_Click(object sender, EventArgs e)
        {
            frm_select_partner select_partner = new frm_select_partner();
            select_partner.parent_form = this;
            select_partner.Show();
            this.Close();
        }

       
    }
}
