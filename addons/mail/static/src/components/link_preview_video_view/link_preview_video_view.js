/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class LinkPreviewVideoView extends Component {

    /**
     * @returns {LinkPreviewVideoView}
     */
    get linkPreviewVideoView() {
        return this.props.record;
    }

}

Object.assign(LinkPreviewVideoView, {
    props: { record: Object },
    template: 'mail.LinkPreviewVideoView',
});

registerMessagingComponent(LinkPreviewVideoView);
