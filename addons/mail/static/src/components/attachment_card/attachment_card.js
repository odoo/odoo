/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
const { Component } = owl;

export class AttachmentCard extends Component {

    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'mail.attachment_card_view', propNameAsRecordLocalId: 'attachmentCardViewLocalId' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment_card_view}
     */
    get attachmentCardView() {
        return this.messaging && this.messaging.models['mail.attachment_card_view'].get(this.props.attachmentCardViewLocalId);
    }

}

Object.assign(AttachmentCard, {
    props: {
        attachmentCardViewLocalId: String,
    },
    template: 'mail.AttachmentCard',
});

registerMessagingComponent(AttachmentCard);
