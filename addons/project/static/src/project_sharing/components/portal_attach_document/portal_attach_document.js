/** @odoo-module */

import { PortalFileInput } from '../portal_file_input/portal_file_input';
import { Component } from "@odoo/owl";

export class PortalAttachDocument extends Component {
    static template = "project.PortalAttachDocument";
    static components = { PortalFileInput };
    static props = {
        highlight: { type: Boolean, optional: true },
        onUpload: { type: Function, optional: true },
        beforeOpen: { type: Function, optional: true },
        slots: {
            type: Object,
            shape: {
                default: Object,
            },
        },
        resId: { type: Number, optional: true },
        resModel: { type: String, optional: true },
        multiUpload: { type: Boolean, optional: true },
        hidden: { type: Boolean, optional: true },
        acceptedFileExtensions: { type: String, optional: true },
        token: { type: String, optional: true },
    };
    static defaultProps = {
        acceptedFileExtensions: "*",
        onUpload: () => {},
        route: "/mail/attachment/upload",
        beforeOpen: async () => true,
    };
}
