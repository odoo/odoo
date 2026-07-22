import { Component, useProps } from "@odoo/owl";
import { Dropzone, dropzoneProps } from "@web/core/dropzone/dropzone";

export class MailAttachmentDropzone extends Component {
    static template = "mail.MailAttachmentDropzone";
    static components = { Dropzone };
    props = useProps(dropzoneProps);
}
