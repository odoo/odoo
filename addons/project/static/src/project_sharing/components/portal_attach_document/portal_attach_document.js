/** @odoo-module */

import { PortalFileInput } from '../portal_file_input/portal_file_input';

const { Component } = owl;

export class PortalAttachDocument extends Component {}

PortalAttachDocument.template = 'project.PortalAttachDocument';
PortalAttachDocument.components = { PortalFileInput };
PortalAttachDocument.props = {
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
PortalAttachDocument.defaultProps = {
    acceptedFileExtensions: "*",
    onUpload: () => {},
    route: "/portal/attachment/add",
    beforeOpen: async () => true,
};
