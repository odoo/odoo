import { Component } from "@odoo/owl";
import { Dropzone } from "@web/core/dropzone/dropzone";

export class MailAttachmentDropzone extends Component {
    static template = "mail.MailAttachmentDropzone";
    static components = { Dropzone };
    static props = Dropzone.props;
}
