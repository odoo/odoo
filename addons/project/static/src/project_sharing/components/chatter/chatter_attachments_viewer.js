/** @odoo-module */

import { Component } from "@odoo/owl";

export class ChatterAttachmentsViewer extends Component {
    static template = "project.ChatterAttachmentsViewer";
    static props = {
        attachments: Array,
        canDelete: { type: Boolean, optional: true },
        delete: { type: Function, optional: true },
    };
    static defaultProps = {
        delete: async () => {},
    };
}
