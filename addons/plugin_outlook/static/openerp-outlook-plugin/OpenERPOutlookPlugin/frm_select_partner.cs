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
using outlook = Microsoft.Office.Interop.Outlook;

namespace OpenERPOutlookPlugin
{

    public partial class frm_select_partner : Form
    {
        public frm_select_partner()
        {
            InitializeComponent();
           
        }
        public Form parent_form = null;

        private void btn_select_partner_select_Click(object sender, EventArgs e)
        {
            try
            {
                if (lstbox_select_partner.SelectedItem == null)
                {
                    throw new Exception("Please select a partner from the list.");
                }
                else
                {
                    txt_select_partner.Text = lstbox_select_partner.SelectedItem.ToString();
                    int partner_id = (int)Cache.OpenERPOutlookPlugin.CreatePartnerRecord(lstbox_select_partner.SelectedItem.ToString());
                    foreach (outlook.MailItem mailItem in Tools.MailItems())
                    {
                        Cache.OpenERPOutlookPlugin.CreateContactRecord(partner_id, mailItem.SenderName, mailItem.SenderEmailAddress);
                    }
                    this.Close();
                }
            }
            catch (Exception ex)
            {
                Connect.handleException(ex);
            }
        }

        private void btn_select_partner_close_Click(object sender, EventArgs e)
        {
            this.Close();
        }

        public void search_lst_partner()
        {
            /*
            * Will search the list of partners as per the given search criteria.
            */
            try
            {
                lstbox_select_partner.Items.Clear();
                foreach (Record oo in Cache.OpenERPOutlookPlugin.SearchRecord(txt_select_partner.Text, "res.partner"))
                {
                    lstbox_select_partner.Items.Add(oo.name);
                }
                if (lstbox_select_partner.Items.Count == 0)
                {
                    Connect.displayMessage("No matching Partner(s) found.");
                }
            }
            catch (Exception ex)
            {
                Connect.handleException(ex);
            }
        }

        private void btn_select_partner_search_Click(object sender, EventArgs e)
        {
            search_lst_partner();
        }

        public string SelectPartnerText
        {
            /*
             * Will gets and sets the selected partner from the list of partners.
             */
            get
            {
                return this.txt_select_partner.Text;
            }
            set
            {
                this.txt_select_partner.Text = value;
            }
        }

        private void frm_select_partner_Load(object sender, EventArgs e)
        {
            Record[] partenr_list = Cache.OpenERPOutlookPlugin.SearchRecord(null,"res.partner");

            foreach (Record partner in partenr_list)
            {
                lstbox_select_partner.Items.Add(partner.name);
            }
        }
    }
}
