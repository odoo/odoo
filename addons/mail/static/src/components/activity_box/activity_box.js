/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import Activity from '@mail/components/activity/activity';

const { Component } = owl;

const components = { Activity };

class ActivityBox extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const chatter = this.env.models['mail.chatter'].get(props.chatterLocalId);
            const thread = chatter && chatter.thread;
            return {
                chatter: chatter ? chatter.__state : undefined,
                thread: thread && thread.__state,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Chatter}
     */
    get chatter() {
        return this.env.models['mail.chatter'].get(this.props.chatterLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickTitle() {
        this.chatter.toggleActivityBoxVisibility();
    }

}

Object.assign(ActivityBox, {
    components,
    props: {
        chatterLocalId: String,
    },
    template: 'mail.ActivityBox',
});

export default ActivityBox;
