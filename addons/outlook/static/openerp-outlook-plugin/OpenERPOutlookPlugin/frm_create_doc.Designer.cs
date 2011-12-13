namespace OpenERPOutlookPlugin
{
    partial class frm_create_doc
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(frm_create_doc));
            this.grp_create_bx = new System.Windows.Forms.GroupBox();
            this.btn_main_close = new System.Windows.Forms.Button();
            this.cmboboxcreate = new System.Windows.Forms.ComboBox();
            this.btn_create_doc = new System.Windows.Forms.Button();
            this.lbtypedoc = new System.Windows.Forms.Label();
            this.grp_create_bx.SuspendLayout();
            this.SuspendLayout();
            // 
            // grp_create_bx
            // 
            this.grp_create_bx.Controls.Add(this.btn_main_close);
            this.grp_create_bx.Controls.Add(this.cmboboxcreate);
            this.grp_create_bx.Controls.Add(this.btn_create_doc);
            this.grp_create_bx.Controls.Add(this.lbtypedoc);
            this.grp_create_bx.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.grp_create_bx.Location = new System.Drawing.Point(12, 12);
            this.grp_create_bx.Name = "grp_create_bx";
            this.grp_create_bx.Size = new System.Drawing.Size(438, 104);
            this.grp_create_bx.TabIndex = 0;
            this.grp_create_bx.TabStop = false;
            this.grp_create_bx.Text = "Create Document";
            // 
            // btn_main_close
            // 
            this.btn_main_close.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_main_close.Image = global::OpenERPOutlookPlugin.Properties.Resources.Error;
            this.btn_main_close.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btn_main_close.Location = new System.Drawing.Point(353, 63);
            this.btn_main_close.Name = "btn_main_close";
            this.btn_main_close.Size = new System.Drawing.Size(63, 23);
            this.btn_main_close.TabIndex = 9;
            this.btn_main_close.Text = "&Close ";
            this.btn_main_close.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btn_main_close.UseVisualStyleBackColor = true;
            this.btn_main_close.Click += new System.EventHandler(this.btn_main_close_Click);
            // 
            // cmboboxcreate
            // 
            this.cmboboxcreate.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.cmboboxcreate.FormattingEnabled = true;
            this.cmboboxcreate.Items.AddRange(new object[] {
            ""});
            this.cmboboxcreate.Location = new System.Drawing.Point(127, 30);
            this.cmboboxcreate.Name = "cmboboxcreate";
            this.cmboboxcreate.Size = new System.Drawing.Size(289, 21);
            this.cmboboxcreate.TabIndex = 6;
            // 
            // btn_create_doc
            // 
            this.btn_create_doc.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_create_doc.Image = global::OpenERPOutlookPlugin.Properties.Resources.Archive;
            this.btn_create_doc.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btn_create_doc.Location = new System.Drawing.Point(279, 63);
            this.btn_create_doc.Name = "btn_create_doc";
            this.btn_create_doc.Size = new System.Drawing.Size(68, 23);
            this.btn_create_doc.TabIndex = 5;
            this.btn_create_doc.Text = "&Create ";
            this.btn_create_doc.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btn_create_doc.UseVisualStyleBackColor = true;
            this.btn_create_doc.Click += new System.EventHandler(this.btn_create_doc_Click);
            // 
            // lbtypedoc
            // 
            this.lbtypedoc.AutoSize = true;
            this.lbtypedoc.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.lbtypedoc.Location = new System.Drawing.Point(6, 33);
            this.lbtypedoc.Name = "lbtypedoc";
            this.lbtypedoc.Size = new System.Drawing.Size(119, 13);
            this.lbtypedoc.TabIndex = 4;
            this.lbtypedoc.Text = "Type of Document :";
            // 
            // frm_create_doc
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(462, 135);
            this.Controls.Add(this.grp_create_bx);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.Fixed3D;
            this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
            this.Name = "frm_create_doc";
            this.Text = "Create new Document";
            this.grp_create_bx.ResumeLayout(false);
            this.grp_create_bx.PerformLayout();
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.GroupBox grp_create_bx;
        private System.Windows.Forms.ComboBox cmboboxcreate;
        private System.Windows.Forms.Button btn_create_doc;
        private System.Windows.Forms.Label lbtypedoc;
        private System.Windows.Forms.Button btn_main_close;
    }
}