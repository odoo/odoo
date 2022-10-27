/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class CallActionListView extends Component {

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

Object.assign(CallActionListView, {
    props: { record: Object },
    template: 'mail.CallActionListView',
});

registerMessagingComponent(CallActionListView);
