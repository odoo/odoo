/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { LegacyComponent } from "@web/legacy/legacy_component";

const { Component } = owl;

export class AttachmentCard extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'AttachmentCard' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {AttachmentCard}
     */
    get attachmentCard() {
        return this.messaging && this.messaging.models['AttachmentCard'].get(this.props.localId);
    }

}

Object.assign(AttachmentCard, {
    props: { localId: String },
    template: 'mail.AttachmentCard',
});

registerMessagingComponent(AttachmentCard);
