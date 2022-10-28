/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

// TODO a nice-to-have would be a resize handle under the videos.

export class CallView extends Component {

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {CallView}
     */
    get callView() {
        return this.props.record;
    }

}

Object.assign(CallView, {
    props: { record: Object },
    template: 'mail.CallView',
});

registerMessagingComponent(CallView);
