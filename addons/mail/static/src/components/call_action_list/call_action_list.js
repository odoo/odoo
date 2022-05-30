/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Popover from "web.Popover";

const { Component } = owl;

export class CallActionList extends Component {

    /**
     * @returns {CallActionListView}
     */
    get callActionListView() {
        return this.props.record;
    }

}

Object.assign(CallActionList, {
    props: { record: Object },
    template: 'mail.CallActionList',
    components: { Popover },
});

registerMessagingComponent(CallActionList);
