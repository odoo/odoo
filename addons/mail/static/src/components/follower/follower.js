/** @odoo-module **/

import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { FollowerSubtypeList } from '@mail/components/follower_subtype_list/follower_subtype_list';

const { Component } = owl;

const components = { FollowerSubtypeList };

export class Follower extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
        useShouldUpdateBasedOnProps();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.follower}
     */
    get follower() {
        return this.env.models['mail.follower'].get(this.props.followerLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickDetails(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.follower.openProfile();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickEdit(ev) {
        ev.preventDefault();
        this.follower.showSubtypes();
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRemove(ev) {
        this.follower.remove();
    }

}

Object.assign(Follower, {
    components,
    props: {
        followerLocalId: String,
    },
    template: 'mail.Follower',
});
