/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ChannelPreviewView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'markAsReadRef', refName: 'markAsRead' });
    }

    /**
     * @returns {ChannelPreviewView}
     */
    get channelPreviewView() {
        return this.props.record;
    }

}

Object.assign(ChannelPreviewView, {
    props: { record: Object },
    template: 'mail.ChannelPreviewView',
});

registerMessagingComponent(ChannelPreviewView);
