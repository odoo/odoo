/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadNeedactionPreview extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'markAsReadRef', refName: 'markAsRead' });
    }

    /**
     * @returns {ThreadNeedactionPreviewView}
     */
    get threadNeedactionPreviewView() {
        return this.props.record;
    }

}

Object.assign(ThreadNeedactionPreview, {
    props: { record: Object },
    template: 'mail.ThreadNeedactionPreview',
});

registerMessagingComponent(ThreadNeedactionPreview);
