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
    public partial class frm_partner : Form
    {

        public frm_partner()
        {
            InitializeComponent();
        }

        public Form parent_form = null;

        private void btnsave_Click(object sender, EventArgs e)
        {
            try
            {

                if (txt_create_partner.Text == "")
                {
                    throw new Exception ("You must enter a Partner Name.");
                }

                else
                {


                    Record[] partners = Cache.OpenERPOutlookPlugin.SearchPartnerByName(txt_create_partner.Text);
                    if (partners != null && partners.Length > 0)
                    {
                        throw new Exception("Partner already exist.");
                    }
                    else
                    {
                        frm_select_partner sel_partner = (frm_select_partner)this.parent_form;
                        sel_partner.SelectPartnerText = txt_create_partner.Text;
                        sel_partner.search_lst_partner();
                        this.Close();
                    }
                }
            }
            catch (Exception ex)
            {

                Connect.handleException(ex);
            }

        }

        private void btncncl_Click(object sender, EventArgs e)
        {
            this.Close();
        }
    }
}
