/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

class LinkPreviewCardView extends Component {

    /**
     * @returns {LinkPreviewCardView}
     */
    get linkPreviewCardView() {
        return this.props.record;
    }

}

Object.assign(LinkPreviewCardView, {
    props: { record: Object },
    template: 'mail.LinkPreviewCardView',
});

registerMessagingComponent(LinkPreviewCardView);
