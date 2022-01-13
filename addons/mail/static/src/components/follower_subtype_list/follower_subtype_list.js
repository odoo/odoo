/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class FollowerSubtypeList extends Component {

    /**
     * @override
     */
     setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'FollowerSubtypeList' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {FollowerSubtypeList}
     */
    get followerSubtypeList() {
        return this.messaging && this.messaging.models['FollowerSubtypeList'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on cancel button.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickCancel(ev) {
        this.followerSubtypeList.follower.closeSubtypes();
    }

    /**
     * Called when clicking on apply button.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickApply(ev) {
        this.followerSubtypeList.follower.updateSubtypes();
    }

}

Object.assign(FollowerSubtypeList, {
    props: { localId: String },
    template: 'mail.FollowerSubtypeList',
});

registerMessagingComponent(FollowerSubtypeList);
