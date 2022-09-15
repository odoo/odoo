/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallSettingsMenuView extends Component {

    /**
     * @returns {CallSettingsMenuView}
     */
    get callSettingsMenuView() {
        return this.props.record;
    }

}

Object.assign(CallSettingsMenuView, {
    props: { record: Object },
    template: 'mail.CallSettingsMenuView',
});

registerMessagingComponent(CallSettingsMenuView);
