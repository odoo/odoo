/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class FollowerListMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'dropdownRef', refName: 'dropdown' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @return {FollowerListMenuView}
     */
    get followerListMenuView() {
        return this.props.record;
    }

}

Object.assign(FollowerListMenu, {
    props: { record: Object },
    template: 'mail.FollowerListMenu',
});

registerMessagingComponent(FollowerListMenu);
