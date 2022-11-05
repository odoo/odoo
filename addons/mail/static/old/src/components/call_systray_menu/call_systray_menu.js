/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class CallSystrayMenu extends Component {

    /**
     * @returns {CallSystrayMenu}
     */
    get callSystrayMenu() {
        return this.props.record;
    }

}

Object.assign(CallSystrayMenu, {
    props: { record: Object },
    template: 'mail.CallSystrayMenu',
});

registerMessagingComponent(CallSystrayMenu);
