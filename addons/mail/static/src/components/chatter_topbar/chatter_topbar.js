/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useModels } from '@mail/component_hooks/use_models/use_models';
import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { FollowButton } from '@mail/components/follow_button/follow_button';
import { FollowerListMenu } from '@mail/components/follower_list_menu/follower_list_menu';

const { Component } = owl;

const components = { FollowButton, FollowerListMenu };

export class ChatterTopbar extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useModels();
        useComponentToModel({ fieldName: 'componentChatterTopbar', modelName: 'mail.chatter', propNameAsRecordLocalId: 'chatterLocalId' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.chatter}
     */
    get chatter() {
        return this.env.models['mail.chatter'].get(this.props.chatterLocalId);
    }

}

Object.assign(ChatterTopbar, {
    components,
    props: {
        chatterLocalId: String,
    },
    template: 'mail.ChatterTopbar',
});
