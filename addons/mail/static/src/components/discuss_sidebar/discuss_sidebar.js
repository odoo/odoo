/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class DiscussSidebar extends Component {

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

Object.assign(DiscussSidebar, {
    props: { record: Object },
    template: 'mail.DiscussSidebar',
});

registerMessagingComponent(DiscussSidebar);
