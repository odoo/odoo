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
using System.Linq;
using OpenERPClient;
using outlook = Microsoft.Office.Interop.Outlook;
using System.Windows.Forms;
namespace OpenERPOutlookPlugin
{

    public class OpenERPOutlookPlugin : Model
    {
        public Boolean isLoggedIn
        {
            /*
             
             * This will check that user is logged in or not and gets the value
             * returns : True if loggedIn, False otherwise.
             
             */
            get
            {
                if (this.Connection != null) { return this.Connection.isLoggedIn; }
                return false;
            }
        }

        public OpenERPOutlookPlugin(OpenERPConnect connection)
        {
            this.Connection = connection;
            //this.set_server_method();
        }

        public Record[] SearchRecord(string name,string model)
        {
            /*
             * Gives name and model for search record.
             */
            ArrayList object_list = new ArrayList();
            Model parent_model;
            parent_model = new Model(model);
            ArrayList args = new ArrayList();
            args.Add(parent_model.model);
            if (name != null)
            {
                args.Add(name);
            }
            else
            {
                args.Add("");
            }
            object[] objects = (object[])this.openerp_connect.Execute("plugin.handler", "list_document_get", args.ToArray());
            foreach (object obj in objects)
            {
                Hashtable document = new Hashtable();
                object[] names = (object[])obj;
                document.Add("id", names[0].ToString());
                document.Add("name", names[1].ToString());
                object_list.Add(new Record(document,parent_model));
            }
            return (Record[])object_list.ToArray(typeof(Record));            
        }

        public string Name_get(outlook.MailItem mail)
        {

                string email = Tools.GetHeader(mail);
                object doc = this.openerp_connect.Execute("plugin.handler", "document_get", email);
                object[] name = (object[])doc;
                return name[3].ToString();
     
        }

        public void RedirectWeb(object web_url)
        {
            /*
             * Will open the url into the web browser.
             */
            System.Diagnostics.Process.Start(web_url.ToString());
        }


        public object[] RedirectPartnerPage(outlook.MailItem mail)
        {
            /*
             
             * Will Redirect to the web-browser and open partner.
             * If it will not found partner in res.partner (in contact) then 
               it will open the contact form to create a partner.
               :Param outlook.MailItem mailItem : Outlook Mail item
             */
            string email_id = mail.SenderEmailAddress.ToString();
            Object[] contact = (Object[])this.openerp_connect.Execute("plugin.handler", "partner_get", email_id);
            return contact;

        }

        public void Open_Document(outlook.MailItem mail)
        {
            /*
             * To open document attached in a url.returns the model_id and res_id of the document
               :Param outlook.MailItem mail: Outlook mails.
             */

            string email = Tools.GetHeader(mail);
            object doc = this.openerp_connect.Execute("plugin.handler", "document_get", email);
            object[] url = (object[])doc;            
            this.RedirectWeb(url[2].ToString());
        }       

        public Boolean PushMail(outlook.MailItem mail, string model, int thread_id)
        {
            /*
             
              * This will push the mail as per the selected items from the list.
                :Param outlook.MailItem mail: selected mail from the outlook.
                :Param string model : Model name to push.
                :Param int thread_id : Thread id of the mail.
              * If mail pushed successfully then it returns true.
              * return False if mail Already Exist.
             
             */
                OpenERPOutlookPlugin openerp_outlook = Cache.OpenERPOutlookPlugin;
                OpenERPConnect openerp_connect = openerp_outlook.Connection;
                ArrayList args = new ArrayList();               
                Hashtable vals = new Hashtable();
                string email;
                if (Tools.GetHeader(mail)!= null)
                {
                    email = Tools.GetHeader(mail); //TODO: Outlook.MailItem Should be Converted into MIME Message
                }
                else
                {
                    email = "";
                }
                
                args.Add(model);
                args.Add(email.ToString());
                args.Add(thread_id);              
                Hashtable attachments = Tools.GetAttachments(mail);                
                args.Add(mail.Body);
                args.Add(mail.HTMLBody);
                args.Add(attachments);
                object push_mail = this.Connection.Execute("plugin.handler", "push_message_outlook", args.ToArray());
                object[] push = (object[])push_mail;
                if (Convert.ToInt32(push[1]) == 0)
                {
                   MessageBox.Show(push[3].ToString());

                }
                else
                {
                    this.RedirectWeb(push[2].ToString());      
                }
                return true;
        }       
        public long CreatePartnerRecord(string name)
        {
            /*
             
             * Creates a partner record in res.partner as per the name given in the plugin form.
               :Param String name: Name given to create a partner in the database.
             * Returns a Long value : Partner id.
             
             */
            Record[] partenr_list = this.SearchRecord(name,"res.partner");
            int partner_id = 0;
            foreach (Record partner in partenr_list)
            {
                partner_id = Convert.ToInt16(partner.id);
            }

            return partner_id;
        }
        public void CreateContactRecord(int partner_id, string name, string email_id)
        {
            /*
             
            * Creates a Contact record in the res.partner as per the details given in the 
              plugin form of openERP outlook Plugin.
              :Param string partner_id : Partner id for which it creates a contact
              :Param string name : Contact name 
              :Param string email_id : Email address 
           
            */
            Hashtable values = new Hashtable();
            values.Add("name", name);
            values.Add("email", email_id);            
            ArrayList args = new ArrayList();
            args.Add(values);
            args.Add(partner_id);
            object[] contact = (object[])this.openerp_connect.Execute("plugin.handler", "contact_create", args.ToArray());
            this.RedirectWeb(contact[2].ToString());

          }
   
        public Model[] GetMailModels()
        {
            /*
             
            * function to get objects to display in combo box
            * returns the Array list of models.
            
           */
            ArrayList obj_list = new ArrayList();
            object mail_models = this.Connection.Execute("plugin.handler", "document_type");           
            foreach (object model in (object[])mail_models)
            {
                Model open_model;
                string[] models = (string[])model;
                open_model = new Model(models[0], models[1]);
                open_model.Connection = this.Connection;
                obj_list.Add(open_model);
            }
            return (Model[])obj_list.ToArray(typeof(Model));
        }
    }

}