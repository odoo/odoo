/** @odoo-module */

import { useService } from "@web/core/utils/hooks";

import { ChatterAttachmentsViewer } from "./chatter_attachments_viewer";

const { Component } = owl;

export class ChatterMessages extends Component {
    setup() {
        this.rpc = useService('rpc');
    }

    /**
     * Toggle the visibility of the message.
     *
     * @param {Object} message message to change the visibility
     */
    async toggleMessageVisibility(message) {
        const result = await this.rpc(
            '/mail/update_is_internal',
            { message_id: message.id, is_internal: !message.is_internal },
        );
        this.props.update(message.id, { is_internal: result });
    }
}

ChatterMessages.template = 'project.ChatterMessages';
ChatterMessages.props = {
    messages: Array,
    isUserEmployee: { type: Boolean, optional: true },
    update: { type: Function, optional: true },
};
ChatterMessages.defaultProps = {
    update: (message_id, changes) => {},
};
ChatterMessages.components = { ChatterAttachmentsViewer };
