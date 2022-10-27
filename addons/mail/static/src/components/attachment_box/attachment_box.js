/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class AttachmentBoxView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {AttachmentBoxView|undefined}
     */
    get attachmentBoxView() {
        return this.props.record;
    }

}

Object.assign(AttachmentBoxView, {
    props: { record: Object },
    template: 'mail.AttachmentBoxView',
});

registerMessagingComponent(AttachmentBoxView);
