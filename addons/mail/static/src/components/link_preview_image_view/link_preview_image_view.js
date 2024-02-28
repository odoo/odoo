/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class LinkPreviewImageView extends Component {

    /**
     * @returns {LinkPreviewImageView}
     */
    get linkPreviewImageView() {
        return this.props.record;
    }

}

Object.assign(LinkPreviewImageView, {
    props: { record: Object },
    template: 'mail.LinkPreviewImageView',
});

registerMessagingComponent(LinkPreviewImageView);
