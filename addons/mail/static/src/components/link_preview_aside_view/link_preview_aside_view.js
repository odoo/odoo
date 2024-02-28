/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

class LinkPreviewAsideView extends Component {

    /**
     * @returns {LinkPreviewAsideView}
     */
    get linkPreviewAsideView() {
        return this.props.record;
    }

}

Object.assign(LinkPreviewAsideView, {
    props: { record: Object },
    template: 'mail.LinkPreviewAsideView',
});

registerMessagingComponent(LinkPreviewAsideView);
