/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallSystrayMenuView extends Component {

    /**
     * @returns {CallSystrayMenuView}
     */
    get callSystrayMenuView() {
        return this.props.record;
    }

}

Object.assign(CallSystrayMenuView, {
    props: { record: Object },
    template: 'mail.CallSystrayMenuView',
});

registerMessagingComponent(CallSystrayMenuView);
