/** @odoo-module **/

import { usePosition } from "@web/core/position_hook";
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, useRef } = owl;

export class FollowerListMenu extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'dropdownRef', refName: 'dropdown' });
        this.togglerRef = useRef("toggler");
        usePosition(() => this.togglerRef.el, {
            position: "bottom-end",
        });
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
