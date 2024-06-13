/** @odoo-module */

import { rpc } from "@web/core/network/rpc";

import { ChatterAttachmentsViewer } from "./chatter_attachments_viewer";
import { Component } from "@odoo/owl";

export class ChatterMessages extends Component {
    static template = "project.ChatterMessages";
    static props = {
        messages: Array,
        isUserEmployee: { type: Boolean, optional: true },
        update: { type: Function, optional: true },
    };
    static defaultProps = {
        update: (message_id, changes) => {},
    };
    static components = { ChatterAttachmentsViewer };

    /**
     * Toggle the visibility of the message.
     *
     * @param {Object} message message to change the visibility
     */
    async toggleMessageVisibility(message) {
        const result = await rpc(
            '/mail/update_is_internal',
            { message_id: message.id, is_internal: !message.is_internal },
        );
        this.props.update(message.id, { is_internal: result });
    }
}
