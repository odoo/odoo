/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class FollowerSubtypeList extends Component {

    /**
     * @override
     */
     setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {FollowerSubtypeList}
     */
    get followerSubtypeList() {
        return this.props.record;
    }

}

Object.assign(FollowerSubtypeList, {
    props: { record: Object },
    template: 'mail.FollowerSubtypeList',
});

registerMessagingComponent(FollowerSubtypeList);
