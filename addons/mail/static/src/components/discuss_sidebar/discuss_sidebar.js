/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussSidebarView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'quickSearchInputRef', refName: 'quickSearchInput' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    /**
     * @returns {DiscussSidebarView}
     */
    get discussSidebarView() {
        return this.props.record;
    }

}

Object.assign(DiscussSidebarView, {
    props: { record: Object },
    template: 'mail.DiscussSidebarView',
});

registerMessagingComponent(DiscussSidebarView);
