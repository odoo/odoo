/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

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
