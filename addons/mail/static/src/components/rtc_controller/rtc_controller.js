/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Popover from "web.Popover";

const { Component } = owl;

export class RtcController extends Component {

    /**
     * @returns {RtcController}
     */
    get rtcController() {
        return this.props.record;
    }

}

Object.assign(RtcController, {
    props: { record: Object },
    template: 'mail.RtcController',
    components: { Popover },
});

registerMessagingComponent(RtcController);
