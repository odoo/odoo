/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import ComposerSuggestedRecipient from '@mail/components/composer_suggested_recipient/composer_suggested_recipient';

const { Component } = owl;
const { useState } = owl.hooks;

const components = { ComposerSuggestedRecipient };

class ComposerSuggestedRecipientList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        this.state = useState({
            hasShowMoreButton: false,
        });
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                threadSuggestedRecipientInfoList: thread ? thread.suggestedRecipientInfoList : [],
            };
        }, {
            compareDepth: {
                threadSuggestedRecipientInfoList: 1,
            },
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickShowLess(ev) {
        this.state.hasShowMoreButton = false;
    }

    /**
     * @private
     */
    _onClickShowMore(ev) {
        this.state.hasShowMoreButton = true;
    }

}

Object.assign(ComposerSuggestedRecipientList, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.ComposerSuggestedRecipientList',
});

export default ComposerSuggestedRecipientList;
