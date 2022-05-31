/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/rtc_activity_notice/rtc_activity_notice';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component } = owl;

export class CallSystrayMenuContainer extends Component {

    /**
     * @override
     */
    setup() {
        useModels();
        super.setup();
    }

}

Object.assign(CallSystrayMenuContainer, {
    components: { CallSystrayMenu: getMessagingComponent('CallSystrayMenu') },
    template: 'mail.CallSystrayMenuContainer',
});
