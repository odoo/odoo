/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;
const { useState } = owl.hooks;

export class ComposerSuggestedRecipientList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            hasShowMoreButton: false,
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread}
     */
    get thread() {
        return this.messaging && this.messaging.models['mail.thread'].get(this.props.threadLocalId);
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
    props: {
        threadLocalId: String,
    },
    template: 'mail.ComposerSuggestedRecipientList',
});

registerMessagingComponent(ComposerSuggestedRecipientList);
