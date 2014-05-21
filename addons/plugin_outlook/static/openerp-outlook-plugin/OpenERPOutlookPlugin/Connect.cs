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



namespace OpenERPOutlookPlugin
{
    using System;
    using System.Reflection;
    using System.Runtime.InteropServices;
    using System.Windows.Forms;
    using office = Microsoft.Office.Core;
    using outlook = Microsoft.Office.Interop.Outlook;
    using OpenERPClient;


    

    #region Read me for Add-in installation and setup information.
    // When run, the Add-in wizard prepared the registry for the Add-in.
    // At a later time, if the Add-in becomes unavailable for reasons such as:
    //   1) You moved this project to a computer other than which is was originally created on.
    //   2) You chose 'Yes' when presented with a message asking if you wish to remove the Add-in.
    //   3) Registry corruption.
    // you will need to re-register the Add-in by building the OpenERPOutlookPluginSetup project, 
    // right click the project in the Solution Explorer, then choose install.
    #endregion

    /// <summary>
    ///   The object for implementing an Add-in.
    /// </summary>
    /// <seealso class='IDTExtensibility2' />

    [GuidAttribute("C86B5760-1254-4F40-BD25-2094A2A678C4"), ProgId("OpenERPOutlookPlugin.Connect")]
    public class Connect : Object, Extensibility.IDTExtensibility2
    {
        /// <summary>
        ///		Implements the constructor for the Add-in object.
        ///		Place your initialization code within this method.
        /// </summary>

        public Connect()
        {

        }

        public int cnt_mail = 0;

        /// <summary>
        ///      Implements the OnConnection method of the IDTExtensibility2 interface.
        ///      Receives notification that the Add-in is being loaded.
        /// </summary>
        /// <param term='application'>
        ///      Root object of the host application.
        /// </param>
        /// <param term='connectMode'>
        ///      Describes how the Add-in is being loaded.
        /// </param>
        /// <param term='addInInst'>
        ///      Object representing this Add-in.
        /// </param>
        /// <seealso class='IDTExtensibility2' />
        public void OnConnection(object application, Extensibility.ext_ConnectMode connectMode, object addInInst, ref System.Array custom)
        {
            applicationObject = application;
            addInInstance = addInInst;

            if (connectMode != Extensibility.ext_ConnectMode.ext_cm_Startup)
            {
                OnStartupComplete(ref custom);
                
            }
        }

        /// <summary>
        ///     Implements the OnDisconnection method of the IDTExtensibility2 interface.
        ///     Receives notification that the Add-in is being unloaded.
        /// </summary>
        /// <param term='disconnectMode'>
        ///      Describes how the Add-in is being unloaded.
        /// </param>
        /// <param term='custom'>
        ///      Array of parameters that are host application specific.
        /// </param>
        /// <seealso class='IDTExtensibility2' />
        public void OnDisconnection(Extensibility.ext_DisconnectMode disconnectMode, ref System.Array custom)
        {
            if (disconnectMode != Extensibility.ext_DisconnectMode.ext_dm_HostShutdown)
            {
                OnBeginShutdown(ref custom);
            }
            applicationObject = null;
        }

        /// <summary>
        ///      Implements the OnAddInsUpdate method of the IDTExtensibility2 interface.
        ///      Receives notification that the collection of Add-ins has changed.
        /// </summary>
        /// <param term='custom'>
        ///      Array of parameters that are host application specific.
        /// </param>
        /// <seealso class='IDTExtensibility2' />
        public void OnAddInsUpdate(ref System.Array custom)
        {
        }

        /// <summary>
        ///      Implements the OnStartupComplete method of the IDTExtensibility2 interface.
        ///      Receives notification that the host application has completed loading.
        /// </summary>
        /// <param term='custom'>
        ///      Array of parameters that are host application specific.
        /// </param>
        /// <seealso class='IDTExtensibility2' />
        /// 
        private office.CommandBarButton btn_open_partner;
        private office.CommandBarButton btn_open_document;
        private office.CommandBarButton btn_open_configuration_form;
        private office.CommandBars oCommandBars;
        private office.CommandBar menuBar;
        private office.CommandBarPopup newMenuBar;

        public int countMail()
        {
            /*
             
             * Gives the number of selected mail.
             * returns: Number of selected mail.
             
             */
            cnt_mail = 0;
            Microsoft.Office.Interop.Outlook.Application app = null;

            app = new Microsoft.Office.Interop.Outlook.Application();
            foreach (var selection in app.ActiveExplorer().Selection)
            {
                cnt_mail = app.ActiveExplorer().Selection.Count;
            }

            return cnt_mail;
        }
      
        public void OnStartupComplete(ref System.Array custom)
        {
            /*
             
             * When outlook is opened it loads a Menu if Outlook plugin is installed.
             * OpenERP - > Push, Partner ,Documents, Configuration
             
             */
            Microsoft.Office.Interop.Outlook.Application app = null;
            try
            {
                app = new Microsoft.Office.Interop.Outlook.Application();
                object omissing = System.Reflection.Missing.Value;
                menuBar = app.ActiveExplorer().CommandBars.ActiveMenuBar;
                ConfigManager config = new ConfigManager();
                config.LoadConfigurationSetting();
                OpenERPOutlookPlugin openerp_outlook = Cache.OpenERPOutlookPlugin;
                OpenERPConnect openerp_connect = openerp_outlook.Connection;
                try
                {
                    if (openerp_connect.URL != null && openerp_connect.DBName != null && openerp_connect.UserId != null && openerp_connect.pswrd != "")
                    {                        
                        string decodpwd = Tools.DecryptB64Pwd(openerp_connect.pswrd);
                        openerp_connect.Login(openerp_connect.DBName, openerp_connect.UserId, decodpwd);                            
                    }
                }
                catch(Exception )
                {
                    MessageBox.Show("Unable to connect remote Server ' " + openerp_connect.URL + " '.", "OpenERP Connection",MessageBoxButtons.OK,MessageBoxIcon.Exclamation);
                }
                newMenuBar = (office.CommandBarPopup)menuBar.Controls.Add(office.MsoControlType.msoControlPopup, omissing, omissing, omissing, true);
                if (newMenuBar != null)
                {
                    newMenuBar.Caption = "OpenERP";
                    newMenuBar.Tag = "My";

                    btn_open_partner = (office.CommandBarButton)newMenuBar.Controls.Add(office.MsoControlType.msoControlButton, omissing, omissing, 1, true);
                    btn_open_partner.Style = office.MsoButtonStyle.msoButtonIconAndCaption;
                    btn_open_partner.Caption = "Contact";
                    //Face ID will use to show the ICON in the left side of the menu.
                    btn_open_partner.FaceId = 3710;
                    newMenuBar.Visible = true;
                    btn_open_partner.Click += new Microsoft.Office.Core._CommandBarButtonEvents_ClickEventHandler(this.btn_open_partner_Click);

                    btn_open_document = (office.CommandBarButton)newMenuBar.Controls.Add(office.MsoControlType.msoControlButton, omissing, omissing, 2, true);
                    btn_open_document.Style = office.MsoButtonStyle.msoButtonIconAndCaption;
                    btn_open_document.Caption = "Documents";
                    //Face ID will use to show the ICON in the left side of the menu.
                    btn_open_document.FaceId = 258;
                    newMenuBar.Visible = true;
                    btn_open_document.Click += new Microsoft.Office.Core._CommandBarButtonEvents_ClickEventHandler(this.btn_open_document_Click);

                    btn_open_configuration_form = (office.CommandBarButton)newMenuBar.Controls.Add(office.MsoControlType.msoControlButton, omissing, omissing, 3, true);
                    btn_open_configuration_form.Style = office.MsoButtonStyle.msoButtonIconAndCaption;
                    btn_open_configuration_form.Caption = "Configuration";
                    //Face ID will use to show the ICON in the left side of the menu.
                    btn_open_configuration_form.FaceId = 5644;
                    newMenuBar.Visible = true;
                    btn_open_configuration_form.Click += new Microsoft.Office.Core._CommandBarButtonEvents_ClickEventHandler(this.btn_open_configuration_form_Click);

                }

            }
            catch (Exception)
            {
                object oActiveExplorer;
                oActiveExplorer = applicationObject.GetType().InvokeMember("ActiveExplorer", BindingFlags.GetProperty, null, applicationObject, null);
                oCommandBars = (office.CommandBars)oActiveExplorer.GetType().InvokeMember("CommandBars", BindingFlags.GetProperty, null, oActiveExplorer, null);
            }
                 

        }

        void btn_open_configuration_form_Click(Microsoft.Office.Core.CommandBarButton Ctrl, ref bool CancelDefault)
        {
            frm_openerp_configuration frm_config = new frm_openerp_configuration();
            frm_config.Show();

        }


        public static bool isLoggedIn()
        {
            /*
             
             * This will check that it is connecting with server or not.
             * If wrong server name or port is given then it will throw the message.
             * returns true If conneted with server, otherwise False.
             
             */
            if (Cache.OpenERPOutlookPlugin == null || Cache.OpenERPOutlookPlugin.isLoggedIn == false)
            {
                throw new Exception("OpenERP Server is not connected!\nPlease connect OpenERP Server from Configuration Menu.");

            }
            return true;
        }

        public static void handleException(Exception e)
        {
            string Title;
            if (Form.ActiveForm != null)
            {
                Title = Form.ActiveForm.Text;
            }
            else
            {
                Title = "OpenERP Addin";
            }
            MessageBox.Show(e.Message, Title, MessageBoxButtons.OK, MessageBoxIcon.Exclamation);
        }
        public static void displayMessage(string message)
        {
            string Title;
            if (Form.ActiveForm != null)
            {
                Title = Form.ActiveForm.Text;
            }
            else
            {
                Title = "OpenERP Addin";
            }
            MessageBox.Show(message, Title, MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        public void CheckMailCount()
        {
            if (countMail() == 0)
            {
                throw new Exception("No email selected.\nPlease select one email.");
            }
            if (countMail() > 1)
            {
                throw new Exception("Multiple selction is not allowed.\nPlease select only one email.");
            }

        }
       
        void btn_open_partner_Click(Microsoft.Office.Core.CommandBarButton Ctrl, ref bool CancelDefault)
        {
            try
            {
                Connect.isLoggedIn();
                this.CheckMailCount(); 
                if (countMail() == 1)
                {

                    foreach (outlook.MailItem mailitem in Tools.MailItems())
                    {
                        

                        Object[] contact = Cache.OpenERPOutlookPlugin.RedirectPartnerPage(mailitem);
                        if ((int)contact[1] > 0)
                        {
                            Cache.OpenERPOutlookPlugin.RedirectWeb(contact[2]);
                        }
                        else
                        {
                            frm_contact contact_form = new frm_contact(mailitem.SenderName, mailitem.SenderEmailAddress);
                            contact_form.Show();
                        }

                    }
                }

            }
            catch (Exception e)
            {
                Connect.handleException(e);
            }

        }

        void btn_open_document_Click(Microsoft.Office.Core.CommandBarButton Ctrl, ref bool CancelDefault)
        {
            try
            {
                Connect.isLoggedIn();
                this.CheckMailCount(); 
                if (countMail() == 1)
                {
                    frm_choose_document_opt frm_doc = new frm_choose_document_opt();    
                }
            }
            catch (Exception e)
            {
                Connect.handleException(e);
            }

        }

        
        public void OnBeginShutdown(ref System.Array custom)
        {
        }
        private object applicationObject;
        private object addInInstance;
    }
}
