/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallActionList extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'moreButtonRef', refName: 'moreButton' });
    }

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
});

registerMessagingComponent(CallActionList);
