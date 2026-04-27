import { Component } from "@odoo/owl";

export class EmbeddedViewLinkPopover extends Component {
    static template = "knowledge.EmbeddedViewLinkPopover";
    static props = {
        close: { type: Function },
        name: { type: String },
        onCopyViewLinkClick: { type: Function },
        onEditViewLinkClick: { type: Function },
        onRemoveViewLinkClick: { type: Function },
        openViewLink: { type: Function },
    };
}
