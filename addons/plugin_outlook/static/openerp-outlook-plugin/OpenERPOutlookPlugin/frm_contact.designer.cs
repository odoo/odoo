namespace OpenERPOutlookPlugin
{
    partial class frm_contact
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(frm_contact));
            this.btnCancel = new System.Windows.Forms.Button();
            this.btnCreate_partner = new System.Windows.Forms.Button();
            this.groupBox1 = new System.Windows.Forms.GroupBox();
            this.txtemail = new System.Windows.Forms.TextBox();
            this.lblemail = new System.Windows.Forms.Label();
            this.txt_contactname_create_contact = new System.Windows.Forms.TextBox();
            this.lblname = new System.Windows.Forms.Label();
            this.btnLink_partner = new System.Windows.Forms.Button();
            this.groupBox1.SuspendLayout();
            this.SuspendLayout();
            // 
            // btnCancel
            // 
            this.btnCancel.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btnCancel.Image = global::OpenERPOutlookPlugin.Properties.Resources.Error;
            this.btnCancel.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btnCancel.Location = new System.Drawing.Point(306, 127);
            this.btnCancel.Name = "btnCancel";
            this.btnCancel.Size = new System.Drawing.Size(70, 23);
            this.btnCancel.TabIndex = 14;
            this.btnCancel.Text = "&Cancel ";
            this.btnCancel.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btnCancel.UseVisualStyleBackColor = true;
            this.btnCancel.Click += new System.EventHandler(this.btnCancel_Click);
            // 
            // btnCreate_partner
            // 
            this.btnCreate_partner.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btnCreate_partner.Image = global::OpenERPOutlookPlugin.Properties.Resources.Success;
            this.btnCreate_partner.ImageAlign = System.Drawing.ContentAlignment.TopLeft;
            this.btnCreate_partner.Location = new System.Drawing.Point(189, 127);
            this.btnCreate_partner.Name = "btnCreate_partner";
            this.btnCreate_partner.Size = new System.Drawing.Size(109, 23);
            this.btnCreate_partner.TabIndex = 15;
            this.btnCreate_partner.Text = "Create &Partner";
            this.btnCreate_partner.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btnCreate_partner.UseVisualStyleBackColor = true;
            this.btnCreate_partner.Click += new System.EventHandler(this.btnCreate_partner_Click);
            // 
            // groupBox1
            // 
            this.groupBox1.Controls.Add(this.txtemail);
            this.groupBox1.Controls.Add(this.lblemail);
            this.groupBox1.Controls.Add(this.txt_contactname_create_contact);
            this.groupBox1.Controls.Add(this.lblname);
            this.groupBox1.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.groupBox1.Location = new System.Drawing.Point(12, 9);
            this.groupBox1.Name = "groupBox1";
            this.groupBox1.Size = new System.Drawing.Size(369, 110);
            this.groupBox1.TabIndex = 16;
            this.groupBox1.TabStop = false;
            this.groupBox1.Text = "Address Detail";
            // 
            // txtemail
            // 
            this.txtemail.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.txtemail.Location = new System.Drawing.Point(97, 66);
            this.txtemail.Name = "txtemail";
            this.txtemail.Size = new System.Drawing.Size(255, 20);
            this.txtemail.TabIndex = 35;
            // 
            // lblemail
            // 
            this.lblemail.AutoSize = true;
            this.lblemail.Location = new System.Drawing.Point(59, 69);
            this.lblemail.Name = "lblemail";
            this.lblemail.Size = new System.Drawing.Size(41, 13);
            this.lblemail.TabIndex = 34;
            this.lblemail.Text = "Email:";
            // 
            // txt_contactname_create_contact
            // 
            this.txt_contactname_create_contact.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.txt_contactname_create_contact.Location = new System.Drawing.Point(97, 26);
            this.txt_contactname_create_contact.Name = "txt_contactname_create_contact";
            this.txt_contactname_create_contact.Size = new System.Drawing.Size(255, 20);
            this.txt_contactname_create_contact.TabIndex = 33;
            // 
            // lblname
            // 
            this.lblname.AutoSize = true;
            this.lblname.Location = new System.Drawing.Point(9, 29);
            this.lblname.Name = "lblname";
            this.lblname.Size = new System.Drawing.Size(91, 13);
            this.lblname.TabIndex = 27;
            this.lblname.Text = "Contact Name:";
            // 
            // btnLink_partner
            // 
            this.btnLink_partner.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btnLink_partner.Image = global::OpenERPOutlookPlugin.Properties.Resources.Search;
            this.btnLink_partner.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btnLink_partner.Location = new System.Drawing.Point(63, 127);
            this.btnLink_partner.Name = "btnLink_partner";
            this.btnLink_partner.Size = new System.Drawing.Size(118, 23);
            this.btnLink_partner.TabIndex = 19;
            this.btnLink_partner.Text = "&Link To Partner";
            this.btnLink_partner.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btnLink_partner.UseVisualStyleBackColor = true;
            this.btnLink_partner.Click += new System.EventHandler(this.btnLink_partner_Click);
            // 
            // frm_contact
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(394, 159);
            this.Controls.Add(this.btnLink_partner);
            this.Controls.Add(this.groupBox1);
            this.Controls.Add(this.btnCreate_partner);
            this.Controls.Add(this.btnCancel);
            this.Cursor = System.Windows.Forms.Cursors.Default;
            this.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.Fixed3D;
            this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
            this.MaximizeBox = false;
            this.Name = "frm_contact";
            this.Text = "Create Contact";
            this.groupBox1.ResumeLayout(false);
            this.groupBox1.PerformLayout();
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.Button btnCancel;
        private System.Windows.Forms.Button btnCreate_partner;
        private System.Windows.Forms.GroupBox groupBox1;
        private System.Windows.Forms.TextBox txt_contactname_create_contact;
        private System.Windows.Forms.Label lblname;
        private System.Windows.Forms.TextBox txtemail;
        private System.Windows.Forms.Label lblemail;
        private System.Windows.Forms.Button btnLink_partner;
    }
}