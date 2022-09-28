/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallSettingsMenu extends Component {

    /**
     * @returns {CallSettingsMenu}
     */
    get callSettingsMenu() {
        return this.props.record;
    }

}

Object.assign(CallSettingsMenu, {
    props: { record: Object },
    template: 'mail.CallSettingsMenu',
});

registerMessagingComponent(CallSettingsMenu);
