/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models';
// ensure components are registered beforehand.
import '@mail/components/rtc_activity_notice/rtc_activity_notice';
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component, useSubEnv } = owl;

export class RtcActivityNoticeContainer extends Component {

    /**
     * @override
     */
    setup() {
        // for now, the legacy env is needed for internal functions such as
        // `useModels` to work
        useSubEnv(Component.env);
        useModels();
        super.setup();
    }

}

Object.assign(RtcActivityNoticeContainer, {
    components: { RtcActivityNotice: getMessagingComponent('RtcActivityNotice') },
    template: 'mail.RtcActivityNoticeContainer',
});
