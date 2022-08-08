/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadPreview extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'markAsReadRef', refName: 'markAsRead' });
    }

    /**
     * @returns {ThreadPreviewView}
     */
    get threadPreviewView() {
        return this.props.record;
    }

}

Object.assign(ThreadPreview, {
    props: { record: Object },
    template: 'mail.ThreadPreview',
});

registerMessagingComponent(ThreadPreview);
