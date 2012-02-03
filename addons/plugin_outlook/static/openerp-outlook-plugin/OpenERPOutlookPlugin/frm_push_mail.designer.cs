namespace OpenERPOutlookPlugin
{
    partial class frm_push_mail
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(frm_push_mail));
            this.groupBox1 = new System.Windows.Forms.GroupBox();
            this.btn_search = new System.Windows.Forms.Button();
            this.txt_doc_search = new System.Windows.Forms.TextBox();
            this.lbtsrch = new System.Windows.Forms.Label();
            this.cmboboxcreate = new System.Windows.Forms.ComboBox();
            this.lbtypedoc = new System.Windows.Forms.Label();
            this.lstview_object = new System.Windows.Forms.ListView();
            this.colheadname = new System.Windows.Forms.ColumnHeader();
            this.colheadmodelname = new System.Windows.Forms.ColumnHeader();
            this.btn_attach_mail_to_partner = new System.Windows.Forms.Button();
            this.lbldocs = new System.Windows.Forms.Label();
            this.groupBox1.SuspendLayout();
            this.SuspendLayout();
            // 
            // groupBox1
            // 
            this.groupBox1.Controls.Add(this.btn_search);
            this.groupBox1.Controls.Add(this.txt_doc_search);
            this.groupBox1.Controls.Add(this.lbtsrch);
            this.groupBox1.Controls.Add(this.cmboboxcreate);
            this.groupBox1.Controls.Add(this.lbtypedoc);
            this.groupBox1.Controls.Add(this.lstview_object);
            this.groupBox1.Controls.Add(this.btn_attach_mail_to_partner);
            this.groupBox1.Controls.Add(this.lbldocs);
            this.groupBox1.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.groupBox1.Location = new System.Drawing.Point(13, 12);
            this.groupBox1.Name = "groupBox1";
            this.groupBox1.Size = new System.Drawing.Size(440, 460);
            this.groupBox1.TabIndex = 3;
            this.groupBox1.TabStop = false;
            this.groupBox1.Text = "Link to an Existing Document";
            // 
            // btn_search
            // 
            this.btn_search.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_search.Image = global::OpenERPOutlookPlugin.Properties.Resources.Search;
            this.btn_search.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btn_search.Location = new System.Drawing.Point(364, 59);
            this.btn_search.Name = "btn_search";
            this.btn_search.Size = new System.Drawing.Size(70, 23);
            this.btn_search.TabIndex = 15;
            this.btn_search.Text = "&Search ";
            this.btn_search.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btn_search.UseVisualStyleBackColor = true;
            this.btn_search.Click += new System.EventHandler(this.btn_search_Click);
            // 
            // txt_doc_search
            // 
            this.txt_doc_search.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.txt_doc_search.Location = new System.Drawing.Point(104, 59);
            this.txt_doc_search.Name = "txt_doc_search";
            this.txt_doc_search.Size = new System.Drawing.Size(254, 20);
            this.txt_doc_search.TabIndex = 14;
            // 
            // lbtsrch
            // 
            this.lbtsrch.AutoSize = true;
            this.lbtsrch.Location = new System.Drawing.Point(32, 59);
            this.lbtsrch.Name = "lbtsrch";
            this.lbtsrch.Size = new System.Drawing.Size(51, 13);
            this.lbtsrch.TabIndex = 13;
            this.lbtsrch.Text = "Search:";
            // 
            // cmboboxcreate
            // 
            this.cmboboxcreate.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.cmboboxcreate.FormattingEnabled = true;
            this.cmboboxcreate.Items.AddRange(new object[] {
            ""});
            this.cmboboxcreate.Location = new System.Drawing.Point(104, 24);
            this.cmboboxcreate.Name = "cmboboxcreate";
            this.cmboboxcreate.Size = new System.Drawing.Size(330, 21);
            this.cmboboxcreate.TabIndex = 12;
            this.cmboboxcreate.SelectedIndexChanged += new System.EventHandler(this.cmboboxcreate_SelectedIndexChanged);
            // 
            // lbtypedoc
            // 
            this.lbtypedoc.AutoSize = true;
            this.lbtypedoc.Location = new System.Drawing.Point(15, 24);
            this.lbtypedoc.Name = "lbtypedoc";
            this.lbtypedoc.Size = new System.Drawing.Size(68, 13);
            this.lbtypedoc.TabIndex = 11;
            this.lbtypedoc.Text = "Document:";
            // 
            // lstview_object
            // 
            this.lstview_object.Alignment = System.Windows.Forms.ListViewAlignment.Default;
            this.lstview_object.AllowColumnReorder = true;
            this.lstview_object.BackgroundImageTiled = true;
            this.lstview_object.Columns.AddRange(new System.Windows.Forms.ColumnHeader[] {
            this.colheadname,
            this.colheadmodelname});
            this.lstview_object.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.lstview_object.FullRowSelect = true;
            this.lstview_object.GridLines = true;
            this.lstview_object.HideSelection = false;
            this.lstview_object.Location = new System.Drawing.Point(9, 110);
            this.lstview_object.Name = "lstview_object";
            this.lstview_object.Size = new System.Drawing.Size(425, 299);
            this.lstview_object.TabIndex = 10;
            this.lstview_object.UseCompatibleStateImageBehavior = false;
            this.lstview_object.View = System.Windows.Forms.View.Details;
            // 
            // colheadname
            // 
            this.colheadname.Text = "Name";
            this.colheadname.Width = 247;
            // 
            // colheadmodelname
            // 
            this.colheadmodelname.Text = "Model Name";
            this.colheadmodelname.Width = 400;
            // 
            // btn_attach_mail_to_partner
            // 
            this.btn_attach_mail_to_partner.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_attach_mail_to_partner.Image = global::OpenERPOutlookPlugin.Properties.Resources.Archive;
            this.btn_attach_mail_to_partner.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btn_attach_mail_to_partner.Location = new System.Drawing.Point(377, 424);
            this.btn_attach_mail_to_partner.Name = "btn_attach_mail_to_partner";
            this.btn_attach_mail_to_partner.Size = new System.Drawing.Size(57, 23);
            this.btn_attach_mail_to_partner.TabIndex = 4;
            this.btn_attach_mail_to_partner.Text = "P&ush ";
            this.btn_attach_mail_to_partner.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btn_attach_mail_to_partner.UseVisualStyleBackColor = true;
            this.btn_attach_mail_to_partner.Click += new System.EventHandler(this.btn_attach_mail_to_partner_Click);
            // 
            // lbldocs
            // 
            this.lbldocs.AutoSize = true;
            this.lbldocs.Location = new System.Drawing.Point(9, 91);
            this.lbldocs.Name = "lbldocs";
            this.lbldocs.Size = new System.Drawing.Size(74, 13);
            this.lbldocs.TabIndex = 0;
            this.lbldocs.Text = "Documents:";
            // 
            // frm_push_mail
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(467, 484);
            this.Controls.Add(this.groupBox1);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.Fixed3D;
            this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
            this.KeyPreview = true;
            this.MaximizeBox = false;
            this.Name = "frm_push_mail";
            this.Text = "Push Mail";
            this.Load += new System.EventHandler(this.frm_push_mail_Load);
            this.groupBox1.ResumeLayout(false);
            this.groupBox1.PerformLayout();
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.GroupBox groupBox1;
        private System.Windows.Forms.ListView lstview_object;
        private System.Windows.Forms.ColumnHeader colheadname;
        private System.Windows.Forms.ColumnHeader colheadmodelname;
        private System.Windows.Forms.Button btn_attach_mail_to_partner;
        private System.Windows.Forms.Label lbldocs;
        private System.Windows.Forms.ComboBox cmboboxcreate;
        private System.Windows.Forms.Label lbtypedoc;
        private System.Windows.Forms.Button btn_search;
        private System.Windows.Forms.TextBox txt_doc_search;
        private System.Windows.Forms.Label lbtsrch;

    }
}