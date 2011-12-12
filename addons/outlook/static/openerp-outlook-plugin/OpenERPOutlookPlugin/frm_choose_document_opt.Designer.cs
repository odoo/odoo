namespace OpenERPOutlookPlugin
{
    partial class frm_choose_document_opt
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(frm_choose_document_opt));
            this.btn_doc = new System.Windows.Forms.Button();
            this.btn_cncl = new System.Windows.Forms.Button();
            this.btn_push = new System.Windows.Forms.Button();
            this.btn_newdoc = new System.Windows.Forms.Button();
            this.lbl_docname = new System.Windows.Forms.Label();
            this.SuspendLayout();
            // 
            // btn_doc
            // 
            this.btn_doc.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_doc.Image = global::OpenERPOutlookPlugin.Properties.Resources.Archive;
            this.btn_doc.ImageAlign = System.Drawing.ContentAlignment.MiddleLeft;
            this.btn_doc.Location = new System.Drawing.Point(31, 146);
            this.btn_doc.Name = "btn_doc";
            this.btn_doc.Size = new System.Drawing.Size(169, 32);
            this.btn_doc.TabIndex = 0;
            this.btn_doc.Text = "&Open an existing Document";
            this.btn_doc.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            this.btn_doc.UseVisualStyleBackColor = true;
            this.btn_doc.Click += new System.EventHandler(this.btn_doc_Click);
            // 
            // btn_cncl
            // 
            this.btn_cncl.Anchor = System.Windows.Forms.AnchorStyles.None;
            this.btn_cncl.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_cncl.Image = global::OpenERPOutlookPlugin.Properties.Resources.Error;
            this.btn_cncl.ImageAlign = System.Drawing.ContentAlignment.MiddleLeft;
            this.btn_cncl.Location = new System.Drawing.Point(463, 146);
            this.btn_cncl.Name = "btn_cncl";
            this.btn_cncl.Size = new System.Drawing.Size(105, 32);
            this.btn_cncl.TabIndex = 1;
            this.btn_cncl.Text = "&Cancel";
            this.btn_cncl.UseVisualStyleBackColor = true;
            this.btn_cncl.Click += new System.EventHandler(this.btn_cncl_Click);
            // 
            // btn_push
            // 
            this.btn_push.Anchor = System.Windows.Forms.AnchorStyles.None;
            this.btn_push.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_push.Image = ((System.Drawing.Image)(resources.GetObject("btn_push.Image")));
            this.btn_push.ImageAlign = System.Drawing.ContentAlignment.MiddleLeft;
            this.btn_push.Location = new System.Drawing.Point(231, 146);
            this.btn_push.Name = "btn_push";
            this.btn_push.Size = new System.Drawing.Size(199, 32);
            this.btn_push.TabIndex = 2;
            this.btn_push.Text = "P&ush to an existing Document";
            this.btn_push.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            this.btn_push.UseVisualStyleBackColor = true;
            this.btn_push.Click += new System.EventHandler(this.btn_push_Click);
            // 
            // btn_newdoc
            // 
            this.btn_newdoc.Anchor = ((System.Windows.Forms.AnchorStyles)((((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Bottom)
                        | System.Windows.Forms.AnchorStyles.Left)
                        | System.Windows.Forms.AnchorStyles.Right)));
            this.btn_newdoc.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_newdoc.Image = global::OpenERPOutlookPlugin.Properties.Resources.Create;
            this.btn_newdoc.ImageAlign = System.Drawing.ContentAlignment.MiddleLeft;
            this.btn_newdoc.Location = new System.Drawing.Point(31, 146);
            this.btn_newdoc.Name = "btn_newdoc";
            this.btn_newdoc.Size = new System.Drawing.Size(169, 32);
            this.btn_newdoc.TabIndex = 3;
            this.btn_newdoc.Text = "Create a &new Document";
            this.btn_newdoc.TextAlign = System.Drawing.ContentAlignment.MiddleRight;
            this.btn_newdoc.UseVisualStyleBackColor = true;
            this.btn_newdoc.Click += new System.EventHandler(this.btn_newdoc_Click);
            // 
            // lbl_docname
            // 
            this.lbl_docname.Anchor = System.Windows.Forms.AnchorStyles.Top;
            this.lbl_docname.BorderStyle = System.Windows.Forms.BorderStyle.Fixed3D;
            this.lbl_docname.Font = new System.Drawing.Font("Microsoft Sans Serif", 15F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.lbl_docname.Location = new System.Drawing.Point(12, 20);
            this.lbl_docname.Name = "lbl_docname";
            this.lbl_docname.Size = new System.Drawing.Size(570, 94);
            this.lbl_docname.TabIndex = 7;
            this.lbl_docname.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            // 
            // frm_choose_document_opt
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(594, 204);
            this.Controls.Add(this.lbl_docname);
            this.Controls.Add(this.btn_newdoc);
            this.Controls.Add(this.btn_push);
            this.Controls.Add(this.btn_cncl);
            this.Controls.Add(this.btn_doc);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.Fixed3D;
            this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
            this.MaximizeBox = false;
            this.Name = "frm_choose_document_opt";
            this.Text = "Document";
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.Button btn_doc;
        private System.Windows.Forms.Button btn_cncl;
        private System.Windows.Forms.Button btn_push;
        private System.Windows.Forms.Button btn_newdoc;
        private System.Windows.Forms.Label lbl_docname;
    }
}