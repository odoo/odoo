/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Dialog from 'web.OwlDialog';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';

const { Component } = owl;

export class AttachmentDeleteConfirmDialog extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useComponentToModel({ fieldName: 'componentAttachmentDeleteConfirmDialog', modelName: 'mail.attachment', propNameAsRecordLocalId: 'attachmentLocalId' });
        useRefToModel({ fieldName: 'dialogRef', modelName: 'mail.attachment', propNameAsRecordLocalId: 'attachmentLocalId', refName: 'dialog' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment}
     */
    get attachment() {
        return this.messaging && this.messaging.models['mail.attachment'].get(this.props.attachmentLocalId);
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

}

Object.assign(AttachmentDeleteConfirmDialog, {
    components: { Dialog },
    props: {
        attachmentLocalId: String,
    },
    template: 'mail.AttachmentDeleteConfirmDialog',
});

registerMessagingComponent(AttachmentDeleteConfirmDialog);
