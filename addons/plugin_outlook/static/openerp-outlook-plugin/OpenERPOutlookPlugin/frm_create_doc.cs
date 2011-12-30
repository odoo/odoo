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


﻿using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Windows.Forms;
using OpenERPClient;

namespace OpenERPOutlookPlugin
{
    public partial class frm_create_doc : Form
    {
        public frm_create_doc()
        {
            InitializeComponent();           
            
            foreach (Model model in Cache.OpenERPOutlookPlugin.GetMailModels())
            {
                if (model.ToString() != "")
                {                   
                    cmboboxcreate.Items.Add(model);
                    cmboboxcreate.Items.Remove("");
                }
            }
        }

        private void btn_create_doc_Click(object sender, EventArgs e)
        {
            try
            {
                if (cmboboxcreate.SelectedItem == null)
                {
                    throw new Exception("Please select a document from the document list.");
                }
                else
                {
                    frm_push_mail pushmail = new frm_push_mail();
                    Model model = (Model)cmboboxcreate.SelectedItem;
                    pushmail.push_mail(model.model, 0);
                    this.Close();
                }

            }

            catch (Exception ex)
            {

                Connect.handleException(ex);
            }

        }

        private void btn_main_close_Click(object sender, EventArgs e)
        {
            this.Close();
        }
    }
}
