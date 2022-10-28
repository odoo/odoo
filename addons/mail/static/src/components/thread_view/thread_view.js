/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class ThreadView extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ThreadView}
     */
    get threadView() {
        return this.props.record;
    }

}

Object.assign(ThreadView, {
    props: { record: Object },
    template: 'mail.ThreadView',
});

registerMessagingComponent(ThreadView);
