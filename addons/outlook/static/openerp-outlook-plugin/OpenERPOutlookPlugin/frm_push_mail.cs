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
using System.Windows.Forms;
using OpenERPClient;
using outlook = Microsoft.Office.Interop.Outlook;

namespace OpenERPOutlookPlugin
{

    public partial class frm_push_mail : Form
    {

        public frm_push_mail()
        {
          
                InitializeComponent();                
                cmboboxcreate.Items.Remove("");
        }

       public bool push_mail(string model, int thread_id)
        {
            foreach (outlook.MailItem mailItem in Tools.MailItems())
            {
                Cache.OpenERPOutlookPlugin.PushMail(mailItem, model, thread_id);

            }
            return true;
        }

        private void btn_attach_mail_to_partner_Click(object sender, EventArgs e)
        {
            try
            {
                if (lstview_object.SelectedItems.Count <= 0)
                {
                    throw new Exception("Plese select item from the list to push");
                }
                foreach (ListViewItem lv in lstview_object.SelectedItems)
                {                   
                    this.push_mail(lv.SubItems[1].Name, Convert.ToInt32(lv.Name));                                           
                }                
                this.Close();
            }
            catch (Exception ex)
            {
                Connect.handleException(ex);
            }
        }
       

        private void frm_push_mail_Load(object sender, EventArgs e)
        {
            try
            {

                Model[] document_models = Cache.OpenERPOutlookPlugin.GetMailModels();
                OpenERPOutlookPlugin openerp_outlook = Cache.OpenERPOutlookPlugin;
                OpenERPConnect openerp_connect = openerp_outlook.Connection;

                foreach (Model model in document_models)
                {
                    ListViewItem item = new ListViewItem();
                    item.Name = model.model;
                    item.Text = model.name;
                    cmboboxcreate.Items.Add(model);
                }
            }
            catch (Exception ex)
            {
                Connect.handleException(ex);
            }
        }
        private void add_item_recordlist(Record record)
        {
            ListViewItem item = new ListViewItem(record.name);
            item.Name = record.id.ToString();
            item.Text = record.name;
            ListViewItem.ListViewSubItem subitem = new ListViewItem.ListViewSubItem();
            subitem.Name = record.model.model;
            subitem.Text = cmboboxcreate.SelectedItem.ToString();
            item.SubItems.Add(subitem);            
            lstview_object.Items.Add(item);
        }

        void load_data_list()
        {
            lstview_object.Items.Clear();

            Model model = (Model)cmboboxcreate.SelectedItem;
            ArrayList condition_list = new ArrayList();
            string name = null;
            if (txt_doc_search.Text != "")
            {
                name = txt_doc_search.Text;                
            }
            
            foreach (Record record in Cache.OpenERPOutlookPlugin.SearchRecord(name,model.model))
            {
                this.add_item_recordlist(record);
            }
            if (lstview_object.Items.Count <= 0)
            {
                Connect.displayMessage("No matching Document(s) found.");
            }
            lstview_object.Sort();
        }

        private void cmboboxcreate_SelectedIndexChanged(object sender, EventArgs e)
        {
            try
            {
                this.load_data_list();
            }
            catch (Exception ex)
            { Connect.handleException(ex); }
        }

        private void btn_search_Click(object sender, EventArgs e)
        {
            try
            {
                this.load_data_list();
            }
            catch
            { Connect.displayMessage("Please Enter Search Text"); }
        }
    }
}

