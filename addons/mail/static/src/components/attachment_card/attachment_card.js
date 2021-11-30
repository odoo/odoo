/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
const { Component } = owl;

export class AttachmentCard extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'AttachmentCard', propNameAsRecordLocalId: 'attachmentCardLocalId' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {AttachmentCard}
     */
    get attachmentCard() {
        return this.messaging && this.messaging.models['AttachmentCard'].get(this.props.attachmentCardLocalId);
    }

}

Object.assign(AttachmentCard, {
    props: {
        attachmentCardLocalId: String,
        onAttachmentRemoved: {
            type: Function,
            optional: true,
        },
    },
    template: 'mail.AttachmentCard',
});

registerMessagingComponent(AttachmentCard);
