/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Dialog from 'web.OwlDialog';

const { Component } = owl;
const { useRef } = owl.hooks;

export class AttachmentDeleteConfirmDialog extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Attachment}
     */
    get attachment() {
        return this.messaging && this.messaging.models['Attachment'].get(this.props.attachmentLocalId);
    }

    /**
     * @returns {string}
     */
    getBody() {
        return _.str.sprintf(
            this.env._t(`Do you really want to delete "%s"?`),
            owl.utils.escape(this.attachment.displayName)
        );
    }

    /**
     * @returns {string}
     */
    getTitle() {
        return this.env._t("Confirmation");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickCancel() {
        this.root.comp._close();
    }

    /**
     * @private
     */
    async _onClickOk() {
        await this.attachment.remove();
        this.root.comp._close();
        if (this.props.onAttachmentRemoved) {
            this.props.onAttachmentRemoved({
                attachmentLocalId: this.props.attachmentLocalId,
            })
        }
    }

}

Object.assign(AttachmentDeleteConfirmDialog, {
    components: { Dialog },
    props: {
        attachmentLocalId: String,
        onAttachmentRemoved: {
            type: Function,
            optional: true,
        },
        onClosed: {
            type: Function,
            optional: true,
        }
    },
    template: 'mail.AttachmentDeleteConfirmDialog',
});

registerMessagingComponent(AttachmentDeleteConfirmDialog);
