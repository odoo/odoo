namespace OpenERPOutlookPlugin
{
    partial class frm_select_partner
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(frm_select_partner));
            this.txt_select_partner = new System.Windows.Forms.TextBox();
            this.groupBox1 = new System.Windows.Forms.GroupBox();
            this.lstbox_select_partner = new System.Windows.Forms.ListBox();
            this.btn_select_partner_select = new System.Windows.Forms.Button();
            this.btn_select_partner_close = new System.Windows.Forms.Button();
            this.btn_select_partner_search = new System.Windows.Forms.Button();
            this.groupBox1.SuspendLayout();
            this.SuspendLayout();
            // 
            // txt_select_partner
            // 
            this.txt_select_partner.Location = new System.Drawing.Point(19, 20);
            this.txt_select_partner.Name = "txt_select_partner";
            this.txt_select_partner.Size = new System.Drawing.Size(209, 20);
            this.txt_select_partner.TabIndex = 0;
            // 
            // groupBox1
            // 
            this.groupBox1.Controls.Add(this.lstbox_select_partner);
            this.groupBox1.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.groupBox1.Location = new System.Drawing.Point(13, 51);
            this.groupBox1.Name = "groupBox1";
            this.groupBox1.Size = new System.Drawing.Size(307, 368);
            this.groupBox1.TabIndex = 7;
            this.groupBox1.TabStop = false;
            this.groupBox1.Text = "Partner Name";
            // 
            // lstbox_select_partner
            // 
            this.lstbox_select_partner.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.lstbox_select_partner.FormattingEnabled = true;
            this.lstbox_select_partner.Location = new System.Drawing.Point(6, 27);
            this.lstbox_select_partner.Name = "lstbox_select_partner";
            this.lstbox_select_partner.Size = new System.Drawing.Size(295, 329);
            this.lstbox_select_partner.TabIndex = 4;
            // 
            // btn_select_partner_select
            // 
            this.btn_select_partner_select.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_select_partner_select.Image = global::OpenERPOutlookPlugin.Properties.Resources.Success;
            this.btn_select_partner_select.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btn_select_partner_select.Location = new System.Drawing.Point(192, 432);
            this.btn_select_partner_select.Name = "btn_select_partner_select";
            this.btn_select_partner_select.Size = new System.Drawing.Size(53, 23);
            this.btn_select_partner_select.TabIndex = 6;
            this.btn_select_partner_select.Text = "&Link";
            this.btn_select_partner_select.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btn_select_partner_select.UseVisualStyleBackColor = true;
            this.btn_select_partner_select.Click += new System.EventHandler(this.btn_select_partner_select_Click);
            // 
            // btn_select_partner_close
            // 
            this.btn_select_partner_close.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_select_partner_close.Image = global::OpenERPOutlookPlugin.Properties.Resources.Error;
            this.btn_select_partner_close.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btn_select_partner_close.Location = new System.Drawing.Point(251, 432);
            this.btn_select_partner_close.Name = "btn_select_partner_close";
            this.btn_select_partner_close.Size = new System.Drawing.Size(64, 23);
            this.btn_select_partner_close.TabIndex = 5;
            this.btn_select_partner_close.Text = "&Close ";
            this.btn_select_partner_close.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btn_select_partner_close.UseVisualStyleBackColor = true;
            this.btn_select_partner_close.Click += new System.EventHandler(this.btn_select_partner_close_Click);
            // 
            // btn_select_partner_search
            // 
            this.btn_select_partner_search.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_select_partner_search.Image = ((System.Drawing.Image)(resources.GetObject("btn_select_partner_search.Image")));
            this.btn_select_partner_search.ImageAlign = System.Drawing.ContentAlignment.MiddleLeft;
            this.btn_select_partner_search.Location = new System.Drawing.Point(245, 19);
            this.btn_select_partner_search.Name = "btn_select_partner_search";
            this.btn_select_partner_search.Size = new System.Drawing.Size(75, 23);
            this.btn_select_partner_search.TabIndex = 1;
            this.btn_select_partner_search.Text = "&Search ";
            this.btn_select_partner_search.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btn_select_partner_search.UseVisualStyleBackColor = true;
            this.btn_select_partner_search.Click += new System.EventHandler(this.btn_select_partner_search_Click);
            // 
            // frm_select_partner
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(350, 467);
            this.Controls.Add(this.groupBox1);
            this.Controls.Add(this.btn_select_partner_select);
            this.Controls.Add(this.btn_select_partner_close);
            this.Controls.Add(this.btn_select_partner_search);
            this.Controls.Add(this.txt_select_partner);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.Fixed3D;
            this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
            this.MaximizeBox = false;
            this.Name = "frm_select_partner";
            this.Text = "Select Partner";
            this.Load += new System.EventHandler(this.frm_select_partner_Load);
            this.groupBox1.ResumeLayout(false);
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.TextBox txt_select_partner;
        private System.Windows.Forms.Button btn_select_partner_search;
        private System.Windows.Forms.Button btn_select_partner_close;
        private System.Windows.Forms.Button btn_select_partner_select;
        private System.Windows.Forms.GroupBox groupBox1;
        private System.Windows.Forms.ListBox lstbox_select_partner;
    }
}