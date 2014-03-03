namespace OpenERPOutlookPlugin
{
    partial class frm_openerp_connection
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
            System.ComponentModel.ComponentResourceManager resources = new System.ComponentModel.ComponentResourceManager(typeof(frm_openerp_connection));
            this.groupBox1 = new System.Windows.Forms.GroupBox();
            this.chkSSL = new System.Windows.Forms.CheckBox();
            this.txt_server_port = new System.Windows.Forms.TextBox();
            this.txt_server_host = new System.Windows.Forms.TextBox();
            this.label3 = new System.Windows.Forms.Label();
            this.label2 = new System.Windows.Forms.Label();
            this.btn_server_ok = new System.Windows.Forms.Button();
            this.btn_server_close = new System.Windows.Forms.Button();
            this.groupBox1.SuspendLayout();
            this.SuspendLayout();
            // 
            // groupBox1
            // 
            this.groupBox1.Controls.Add(this.chkSSL);
            this.groupBox1.Controls.Add(this.txt_server_port);
            this.groupBox1.Controls.Add(this.txt_server_host);
            this.groupBox1.Controls.Add(this.label3);
            this.groupBox1.Controls.Add(this.label2);
            this.groupBox1.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.groupBox1.Location = new System.Drawing.Point(22, 13);
            this.groupBox1.Name = "groupBox1";
            this.groupBox1.Size = new System.Drawing.Size(202, 123);
            this.groupBox1.TabIndex = 14;
            this.groupBox1.TabStop = false;
            this.groupBox1.Text = "Connection Parameter";
            // 
            // chkSSL
            // 
            this.chkSSL.AutoSize = true;
            this.chkSSL.Location = new System.Drawing.Point(15, 86);
            this.chkSSL.Name = "chkSSL";
            this.chkSSL.Size = new System.Drawing.Size(89, 17);
            this.chkSSL.TabIndex = 19;
            this.chkSSL.Text = "SSL (https)";
            this.chkSSL.UseVisualStyleBackColor = true;
            this.chkSSL.CheckedChanged += new System.EventHandler(this.chkSSL_CheckedChanged);
            // 
            // txt_server_port
            // 
            this.txt_server_port.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.txt_server_port.Location = new System.Drawing.Point(58, 60);
            this.txt_server_port.Name = "txt_server_port";
            this.txt_server_port.Size = new System.Drawing.Size(138, 20);
            this.txt_server_port.TabIndex = 18;
            this.txt_server_port.Text = "8069";
            // 
            // txt_server_host
            // 
            this.txt_server_host.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Regular, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.txt_server_host.Location = new System.Drawing.Point(58, 34);
            this.txt_server_host.Name = "txt_server_host";
            this.txt_server_host.Size = new System.Drawing.Size(138, 20);
            this.txt_server_host.TabIndex = 17;
            this.txt_server_host.Text = "localhost";
            // 
            // label3
            // 
            this.label3.AutoSize = true;
            this.label3.Location = new System.Drawing.Point(24, 59);
            this.label3.Name = "label3";
            this.label3.Size = new System.Drawing.Size(34, 13);
            this.label3.TabIndex = 16;
            this.label3.Text = "Port:";
            // 
            // label2
            // 
            this.label2.AutoSize = true;
            this.label2.Location = new System.Drawing.Point(12, 34);
            this.label2.Name = "label2";
            this.label2.Size = new System.Drawing.Size(48, 13);
            this.label2.TabIndex = 15;
            this.label2.Text = "Server:";
            // 
            // btn_server_ok
            // 
            this.btn_server_ok.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_server_ok.Image = global::OpenERPOutlookPlugin.Properties.Resources.Success;
            this.btn_server_ok.ImageAlign = System.Drawing.ContentAlignment.TopLeft;
            this.btn_server_ok.Location = new System.Drawing.Point(96, 149);
            this.btn_server_ok.Name = "btn_server_ok";
            this.btn_server_ok.Size = new System.Drawing.Size(49, 23);
            this.btn_server_ok.TabIndex = 13;
            this.btn_server_ok.Text = "&OK ";
            this.btn_server_ok.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btn_server_ok.UseVisualStyleBackColor = true;
            this.btn_server_ok.Click += new System.EventHandler(this.btn_server_ok_Click);
            // 
            // btn_server_close
            // 
            this.btn_server_close.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(0)));
            this.btn_server_close.Image = global::OpenERPOutlookPlugin.Properties.Resources.Error;
            this.btn_server_close.ImageAlign = System.Drawing.ContentAlignment.BottomLeft;
            this.btn_server_close.Location = new System.Drawing.Point(160, 149);
            this.btn_server_close.Name = "btn_server_close";
            this.btn_server_close.Size = new System.Drawing.Size(64, 23);
            this.btn_server_close.TabIndex = 12;
            this.btn_server_close.Text = "&Close ";
            this.btn_server_close.TextAlign = System.Drawing.ContentAlignment.TopRight;
            this.btn_server_close.UseVisualStyleBackColor = true;
            this.btn_server_close.Click += new System.EventHandler(this.btn_server_close_Click);
            // 
            // frm_openerp_connection
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(246, 184);
            this.Controls.Add(this.groupBox1);
            this.Controls.Add(this.btn_server_ok);
            this.Controls.Add(this.btn_server_close);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.Fixed3D;
            this.Icon = ((System.Drawing.Icon)(resources.GetObject("$this.Icon")));
            this.Name = "frm_openerp_connection";
            this.Text = "OpenERP Connection";
            this.Load += new System.EventHandler(this.frm_openerp_connection_Load);
            this.groupBox1.ResumeLayout(false);
            this.groupBox1.PerformLayout();
            this.ResumeLayout(false);

        }

        #endregion

        private System.Windows.Forms.Button btn_server_ok;
        private System.Windows.Forms.Button btn_server_close;
        private System.Windows.Forms.GroupBox groupBox1;
        private System.Windows.Forms.CheckBox chkSSL;
        private System.Windows.Forms.TextBox txt_server_port;
        private System.Windows.Forms.TextBox txt_server_host;
        private System.Windows.Forms.Label label3;
        private System.Windows.Forms.Label label2;
    }
}