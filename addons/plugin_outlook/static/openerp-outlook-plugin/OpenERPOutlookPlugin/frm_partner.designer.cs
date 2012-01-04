namespace OpenERPOutlookPlugin
{
    partial class frm_partner
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(frm_partner));
            this.txt_create_partner = new System.Windows.Forms.TextBox();
            this.lablname = new System.Windows.Forms.Label();
            this.btncncl = new System.Windows.Forms.Button();
            this.btnsave = new System.Windows.Forms.Button();
            this.SuspendLayout();
            // 
            // txt_create_partner
            // 
            this.txt_create_partner.Location = new System.Drawing.Point(87, 26);
            this.txt_create_partner.Name = "txt_create_partner";
            this.txt_create_partner.Size = new System.Drawing.Size(185, 20);
            this.txt_create_partner.TabIndex = 0;
            // 
            // lablname
            // 
            this.lablname.AutoSize = true;
            this.lablname.Location = new System.Drawing.Point(43, 29);
            this.lablname.Name = "lablname";
            this.lablname.Size = new System.Drawing.Size(38, 13);
            this.lablname.TabIndex = 1;
            this.lablname.Text = "Name:";
            // 
            // btncncl
            // 
            this.btncncl.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btncncl.Image = global::OpenERPOutlookPlugin.Properties.Resources.Error;
            this.btncncl.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btncncl.Location = new System.Drawing.Point(205, 75);
            this.btncncl.Name = "btncncl";
            this.btncncl.Size = new System.Drawing.Size(67, 23);
            this.btncncl.TabIndex = 3;
            this.btncncl.Text = "&Cancel";
            this.btncncl.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btncncl.UseVisualStyleBackColor = true;
            this.btncncl.Click += new System.EventHandler(this.btncncl_Click);
            // 
            // btnsave
            // 
            this.btnsave.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btnsave.Image = global::OpenERPOutlookPlugin.Properties.Resources.Success;
            this.btnsave.ImageAlign = System.Drawing.ContentAlignment.TopLeft;
            this.btnsave.Location = new System.Drawing.Point(139, 75);
            this.btnsave.Name = "btnsave";
            this.btnsave.Size = new System.Drawing.Size(60, 23);
            this.btnsave.TabIndex = 2;
            this.btnsave.Text = "&Save ";
            this.btnsave.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btnsave.UseVisualStyleBackColor = true;
            this.btnsave.Click += new System.EventHandler(this.btnsave_Click);
            // 
            // frm_partner
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(284, 110);
            this.Controls.Add(this.btncncl);
            this.Controls.Add(this.btnsave);
            this.Controls.Add(this.lablname);
            this.Controls.Add(this.txt_create_partner);
            this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
            this.Name = "frm_partner";
            this.Text = "Create a new Partner";
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.TextBox txt_create_partner;
        private System.Windows.Forms.Label lablname;
        private System.Windows.Forms.Button btnsave;
        private System.Windows.Forms.Button btncncl;
    }
}