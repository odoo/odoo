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
using outlook = Microsoft.Office.Interop.Outlook;
using System.Collections;

namespace OpenERPOutlookPlugin
{
    public partial class frm_choose_document_opt : Form
    {
        public frm_choose_document_opt()
        {
            InitializeComponent();
            try
            {
                foreach (outlook.MailItem mail in Tools.MailItems())
                {

                    string name_get = Cache.OpenERPOutlookPlugin.Name_get(mail);
                    this.Show();
                    if (name_get != "")
                    {
                        lbl_docname.Text = name_get;
                        btn_newdoc.Visible = false;

                    }
                    else
                    {
                        lbl_docname.Text = mail.Subject;
                        btn_doc.Visible = false;
                    }
                }

            }
            catch (Exception ex)
            {
                Connect.handleException(ex);
            }

        }

        private void btn_doc_Click(object sender, EventArgs e)
        {
            foreach (outlook.MailItem mailitem in Tools.MailItems())
            {
                Cache.OpenERPOutlookPlugin.Open_Document(mailitem);
               
            }
            this.Close();
        }


        private void btn_push_Click(object sender, EventArgs e)
        {
            frm_push_mail frm_push_mail = new frm_push_mail();
            frm_push_mail.Show();
            this.Close();
        }

        private void btn_cncl_Click(object sender, EventArgs e)
        {
            this.Close();
        }

        private void btn_newdoc_Click(object sender, EventArgs e)
        {
            frm_create_doc create_doc = new frm_create_doc();
            create_doc.Show();
            this.Close();
        }

    }
}
