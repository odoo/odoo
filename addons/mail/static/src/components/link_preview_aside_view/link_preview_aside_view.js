/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
