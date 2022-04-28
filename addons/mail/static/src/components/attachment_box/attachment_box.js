/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class AttachmentBox extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'AttachmentBoxView' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {AttachmentBoxView|undefined}
     */
    get attachmentBoxView() {
        return this.messaging && this.messaging.models['AttachmentBoxView'].get(this.props.localId);
    }

}

Object.assign(AttachmentBox, {
    props: { localId: String },
    template: 'mail.AttachmentBox',
});

registerMessagingComponent(AttachmentBox);
