namespace OpenERPOutlookPlugin
{
    partial class frm_openerp_configuration
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(frm_openerp_configuration));
            this.btn_main_close = new System.Windows.Forms.Button();
            this.tbabout = new System.Windows.Forms.TabPage();
            this.groupBox3 = new System.Windows.Forms.GroupBox();
            this.pictureBox1 = new System.Windows.Forms.PictureBox();
            this.richTextBox1 = new System.Windows.Forms.RichTextBox();
            this.tbconfigsetting = new System.Windows.Forms.TabPage();
            this.pnconfig = new System.Windows.Forms.Panel();
            this.chkpwd = new System.Windows.Forms.CheckBox();
            this.txt_dbname = new System.Windows.Forms.TextBox();
            this.combo_config_database = new System.Windows.Forms.ComboBox();
            this.btn_openerp_connect = new System.Windows.Forms.Button();
            this.txt_password = new System.Windows.Forms.TextBox();
            this.txt_username = new System.Windows.Forms.TextBox();
            this.btn_open_server_url_form = new System.Windows.Forms.Button();
            this.txt_server_config = new System.Windows.Forms.TextBox();
            this.lbn_password = new System.Windows.Forms.Label();
            this.lbn_username = new System.Windows.Forms.Label();
            this.lbn_dbname = new System.Windows.Forms.Label();
            this.lbn_server = new System.Windows.Forms.Label();
            this.tb1 = new System.Windows.Forms.TabControl();
            this.tbabout.SuspendLayout();
            this.groupBox3.SuspendLayout();
            ((System.ComponentModel.ISupportInitialize)(this.pictureBox1)).BeginInit();
            this.tbconfigsetting.SuspendLayout();
            this.pnconfig.SuspendLayout();
            this.tb1.SuspendLayout();
            this.SuspendLayout();
            // 
            // btn_main_close
            // 
            this.btn_main_close.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_main_close.Image = global::OpenERPOutlookPlugin.Properties.Resources.Error;
            this.btn_main_close.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btn_main_close.Location = new System.Drawing.Point(801, 420);
            this.btn_main_close.Name = "btn_main_close";
            this.btn_main_close.Size = new System.Drawing.Size(63, 23);
            this.btn_main_close.TabIndex = 8;
            this.btn_main_close.Text = "Close ";
            this.btn_main_close.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btn_main_close.UseVisualStyleBackColor = true;
            this.btn_main_close.Click += new System.EventHandler(this.btn_main_close_Click);
            // 
            // tbabout
            // 
            this.tbabout.Controls.Add(this.groupBox3);
            this.tbabout.Location = new System.Drawing.Point(4, 22);
            this.tbabout.Name = "tbabout";
            this.tbabout.Padding = new System.Windows.Forms.Padding(3);
            this.tbabout.Size = new System.Drawing.Size(434, 315);
            this.tbabout.TabIndex = 2;
            this.tbabout.Text = "About";
            this.tbabout.UseVisualStyleBackColor = true;
            // 
            // groupBox3
            // 
            this.groupBox3.Controls.Add(this.pictureBox1);
            this.groupBox3.Controls.Add(this.richTextBox1);
            this.groupBox3.Dock = System.Windows.Forms.DockStyle.Fill;
            this.groupBox3.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.groupBox3.Location = new System.Drawing.Point(3, 3);
            this.groupBox3.Name = "groupBox3";
            this.groupBox3.Size = new System.Drawing.Size(428, 309);
            this.groupBox3.TabIndex = 0;
            this.groupBox3.TabStop = false;
            this.groupBox3.Text = "OpenERP Outlook Plugin";
            // 
            // pictureBox1
            // 
            this.pictureBox1.Image = ((System.Drawing.Image)(resources.GetObject("pictureBox1.Image")));
            this.pictureBox1.Location = new System.Drawing.Point(109, 92);
            this.pictureBox1.Name = "pictureBox1";
            this.pictureBox1.Size = new System.Drawing.Size(194, 50);
            this.pictureBox1.TabIndex = 1;
            this.pictureBox1.TabStop = false;
            // 
            // richTextBox1
            // 
            this.richTextBox1.BorderStyle = System.Windows.Forms.BorderStyle.None;
            this.richTextBox1.Dock = System.Windows.Forms.DockStyle.Fill;
            this.richTextBox1.Location = new System.Drawing.Point(3, 16);
            this.richTextBox1.Name = "richTextBox1";
            this.richTextBox1.ReadOnly = true;
            this.richTextBox1.Size = new System.Drawing.Size(422, 290);
            this.richTextBox1.TabIndex = 0;
            this.richTextBox1.Text = resources.GetString("richTextBox1.Text");
            this.richTextBox1.LinkClicked += new System.Windows.Forms.LinkClickedEventHandler(this.richTextBox1_LinkClicked);
            // 
            // tbconfigsetting
            // 
            this.tbconfigsetting.Controls.Add(this.pnconfig);
            this.tbconfigsetting.Location = new System.Drawing.Point(4, 22);
            this.tbconfigsetting.Name = "tbconfigsetting";
            this.tbconfigsetting.Padding = new System.Windows.Forms.Padding(3);
            this.tbconfigsetting.Size = new System.Drawing.Size(434, 315);
            this.tbconfigsetting.TabIndex = 0;
            this.tbconfigsetting.Text = "Configuration Settings";
            this.tbconfigsetting.UseVisualStyleBackColor = true;
            // 
            // pnconfig
            // 
            this.pnconfig.Controls.Add(this.chkpwd);
            this.pnconfig.Controls.Add(this.txt_dbname);
            this.pnconfig.Controls.Add(this.combo_config_database);
            this.pnconfig.Controls.Add(this.btn_openerp_connect);
            this.pnconfig.Controls.Add(this.txt_password);
            this.pnconfig.Controls.Add(this.txt_username);
            this.pnconfig.Controls.Add(this.btn_open_server_url_form);
            this.pnconfig.Controls.Add(this.txt_server_config);
            this.pnconfig.Controls.Add(this.lbn_password);
            this.pnconfig.Controls.Add(this.lbn_username);
            this.pnconfig.Controls.Add(this.lbn_dbname);
            this.pnconfig.Controls.Add(this.lbn_server);
            this.pnconfig.Dock = System.Windows.Forms.DockStyle.Fill;
            this.pnconfig.Location = new System.Drawing.Point(3, 3);
            this.pnconfig.Name = "pnconfig";
            this.pnconfig.Size = new System.Drawing.Size(428, 309);
            this.pnconfig.TabIndex = 53;
            // 
            // chkpwd
            // 
            this.chkpwd.AutoSize = true;
            this.chkpwd.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.chkpwd.Location = new System.Drawing.Point(105, 142);
            this.chkpwd.Name = "chkpwd";
            this.chkpwd.Size = new System.Drawing.Size(143, 17);
            this.chkpwd.TabIndex = 67;
            this.chkpwd.Text = "Remember Password";
            this.chkpwd.UseVisualStyleBackColor = true;
            // 
            // txt_dbname
            // 
            this.txt_dbname.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.txt_dbname.Location = new System.Drawing.Point(105, 57);
            this.txt_dbname.Name = "txt_dbname";
            this.txt_dbname.Size = new System.Drawing.Size(269, 20);
            this.txt_dbname.TabIndex = 58;
            this.txt_dbname.Visible = false;
            // 
            // combo_config_database
            // 
            this.combo_config_database.AllowDrop = true;
            this.combo_config_database.Location = new System.Drawing.Point(105, 57);
            this.combo_config_database.Name = "combo_config_database";
            this.combo_config_database.Size = new System.Drawing.Size(269, 21);
            this.combo_config_database.TabIndex = 59;
            // 
            // btn_openerp_connect
            // 
            this.btn_openerp_connect.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_openerp_connect.Image = global::OpenERPOutlookPlugin.Properties.Resources.Success;
            this.btn_openerp_connect.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btn_openerp_connect.Location = new System.Drawing.Point(295, 137);
            this.btn_openerp_connect.Name = "btn_openerp_connect";
            this.btn_openerp_connect.Size = new System.Drawing.Size(79, 23);
            this.btn_openerp_connect.TabIndex = 62;
            this.btn_openerp_connect.Text = "C&onnect ";
            this.btn_openerp_connect.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btn_openerp_connect.UseVisualStyleBackColor = true;
            this.btn_openerp_connect.Click += new System.EventHandler(this.btn_openerp_connect_Click);
            // 
            // txt_password
            // 
            this.txt_password.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.txt_password.Location = new System.Drawing.Point(105, 111);
            this.txt_password.Name = "txt_password";
            this.txt_password.PasswordChar = '*';
            this.txt_password.Size = new System.Drawing.Size(269, 20);
            this.txt_password.TabIndex = 61;
            // 
            // txt_username
            // 
            this.txt_username.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.txt_username.Location = new System.Drawing.Point(105, 84);
            this.txt_username.Name = "txt_username";
            this.txt_username.Size = new System.Drawing.Size(269, 20);
            this.txt_username.TabIndex = 60;
            // 
            // btn_open_server_url_form
            // 
            this.btn_open_server_url_form.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_open_server_url_form.Image = global::OpenERPOutlookPlugin.Properties.Resources.Search;
            this.btn_open_server_url_form.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btn_open_server_url_form.Location = new System.Drawing.Point(299, 28);
            this.btn_open_server_url_form.Name = "btn_open_server_url_form";
            this.btn_open_server_url_form.Size = new System.Drawing.Size(75, 23);
            this.btn_open_server_url_form.TabIndex = 57;
            this.btn_open_server_url_form.Text = "C&hange ";
            this.btn_open_server_url_form.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btn_open_server_url_form.UseVisualStyleBackColor = true;
            this.btn_open_server_url_form.Click += new System.EventHandler(this.btn_open_server_url_form_Click);
            // 
            // txt_server_config
            // 
            this.txt_server_config.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.txt_server_config.Location = new System.Drawing.Point(105, 30);
            this.txt_server_config.Name = "txt_server_config";
            this.txt_server_config.ReadOnly = true;
            this.txt_server_config.Size = new System.Drawing.Size(186, 20);
            this.txt_server_config.TabIndex = 56;
            this.txt_server_config.TabStop = false;
            this.txt_server_config.TextChanged += new System.EventHandler(this.txt_server_config_TextChanged);
            // 
            // lbn_password
            // 
            this.lbn_password.AutoSize = true;
            this.lbn_password.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.lbn_password.Location = new System.Drawing.Point(33, 114);
            this.lbn_password.Name = "lbn_password";
            this.lbn_password.Size = new System.Drawing.Size(69, 13);
            this.lbn_password.TabIndex = 66;
            this.lbn_password.Text = "Password :";
            // 
            // lbn_username
            // 
            this.lbn_username.AutoSize = true;
            this.lbn_username.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.lbn_username.Location = new System.Drawing.Point(34, 86);
            this.lbn_username.Name = "lbn_username";
            this.lbn_username.Size = new System.Drawing.Size(71, 13);
            this.lbn_username.TabIndex = 65;
            this.lbn_username.Text = "Username :";
            // 
            // lbn_dbname
            // 
            this.lbn_dbname.AutoSize = true;
            this.lbn_dbname.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.lbn_dbname.Location = new System.Drawing.Point(34, 57);
            this.lbn_dbname.Name = "lbn_dbname";
            this.lbn_dbname.Size = new System.Drawing.Size(69, 13);
            this.lbn_dbname.TabIndex = 64;
            this.lbn_dbname.Text = "Database :";
            // 
            // lbn_server
            // 
            this.lbn_server.AutoSize = true;
            this.lbn_server.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.lbn_server.Location = new System.Drawing.Point(34, 30);
            this.lbn_server.Name = "lbn_server";
            this.lbn_server.Size = new System.Drawing.Size(72, 13);
            this.lbn_server.TabIndex = 63;
            this.lbn_server.Text = "Server      :";
            // 
            // tb1
            // 
            this.tb1.Controls.Add(this.tbconfigsetting);
            this.tb1.Controls.Add(this.tbabout);
            this.tb1.Dock = System.Windows.Forms.DockStyle.Fill;
            this.tb1.Location = new System.Drawing.Point(0, 0);
            this.tb1.Name = "tb1";
            this.tb1.SelectedIndex = 0;
            this.tb1.Size = new System.Drawing.Size(442, 341);
            this.tb1.TabIndex = 40;
            this.tb1.Tag = "";
            // 
            // frm_openerp_configuration
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(442, 341);
            this.Controls.Add(this.btn_main_close);
            this.Controls.Add(this.tb1);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.Fixed3D;
            this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
            this.MaximizeBox = false;
            this.Name = "frm_openerp_configuration";
            this.Text = "OpenERP Configuration";
            this.Load += new System.EventHandler(this.frm_openerp_configuration_Load);
            this.tbabout.ResumeLayout(false);
            this.groupBox3.ResumeLayout(false);
            ((System.ComponentModel.ISupportInitialize)(this.pictureBox1)).EndInit();
            this.tbconfigsetting.ResumeLayout(false);
            this.pnconfig.ResumeLayout(false);
            this.pnconfig.PerformLayout();
            this.tb1.ResumeLayout(false);
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.Button btn_main_close;
        private System.Windows.Forms.TabPage tbabout;
        private System.Windows.Forms.GroupBox groupBox3;
        private System.Windows.Forms.PictureBox pictureBox1;
        private System.Windows.Forms.RichTextBox richTextBox1;
        private System.Windows.Forms.TabPage tbconfigsetting;
        private System.Windows.Forms.Panel pnconfig;
        private System.Windows.Forms.CheckBox chkpwd;
        private System.Windows.Forms.TextBox txt_dbname;
        private System.Windows.Forms.ComboBox combo_config_database;
        private System.Windows.Forms.Button btn_openerp_connect;
        private System.Windows.Forms.TextBox txt_password;
        private System.Windows.Forms.TextBox txt_username;
        private System.Windows.Forms.Button btn_open_server_url_form;
        private System.Windows.Forms.TextBox txt_server_config;
        private System.Windows.Forms.Label lbn_password;
        private System.Windows.Forms.Label lbn_username;
        private System.Windows.Forms.Label lbn_dbname;
        private System.Windows.Forms.Label lbn_server;
        private System.Windows.Forms.TabControl tb1;

    }
}