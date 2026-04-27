/** @odoo-module **/

import { Component } from "@odoo/owl";

export class DocumentsRemovePartnerButton extends Component {
    static defaultProps = { disabled: false };
    static props = {
        accessPartner: Object,
        disabled: { type: Boolean, optional: true },
        isInternalUser: Boolean,
        isCurrentUser: Function,
        removeAccess: Function,
    };
    static template = "documents.RemovePartnerButton";
}
