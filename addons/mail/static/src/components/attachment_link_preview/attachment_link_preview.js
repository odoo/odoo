/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import AttachmentDeleteConfirmDialog from '@mail/components/attachment_delete_confirm_dialog/attachment_delete_confirm_dialog';

const components = { AttachmentDeleteConfirmDialog };

const { Component, useState } = owl;

class AttachmentLinkPreview extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const attachment = this.env.models['mail.attachment'].get(props.attachmentLocalId);
            return {
                attachment: attachment ? attachment.__state : undefined,
            };
        });
        this.state = useState({
            hasDeleteConfirmDialog: false,
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * @returns {mail.attachment}
     */
    get attachment() {
        return this.env.models['mail.attachment'].get(this.props.attachmentLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUnlink(ev) {
        ev.stopPropagation();
        if (!this.attachment) {
            return;
        }
        if (this.attachment.isLinkedToComposer) {
            this.attachment.remove();
            this.trigger('o-attachment-removed', { attachmentLocalId: this.props.attachmentLocalId });
        } else {
            this.state.hasDeleteConfirmDialog = true;
        }
    }

   /**
    * @private
    */
    _onDeleteConfirmDialogClosed() {
        this.state.hasDeleteConfirmDialog = false;
    }

}

Object.assign(AttachmentLinkPreview, {
    components,
    defaultProps: {
        isCompact: false,
    },
    props: {
        attachmentLocalId: String,
        isCompact: {
            type: Boolean,
            optional: true,
        },
    },
    template: 'mail.AttachmentLinkPreview',
});

export default AttachmentLinkPreview;
