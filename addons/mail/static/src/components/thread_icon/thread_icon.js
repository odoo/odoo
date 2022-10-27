/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class ThreadIconView extends Component {

    /**
     * @returns {ThreadIconView}
     */
    get threadIconView() {
        return this.props.record;
    }

}

Object.assign(ThreadIconView, {
    props: { record: Object },
    template: 'mail.ThreadIconView',
});

registerMessagingComponent(ThreadIconView);
