odoo.define('mail/static/src/components/composer_suggested_recipients_list/composer_suggested_recipients_list.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const { Component } = owl;
const { useState } = owl.hooks;

const components = {
    ComposerSuggestedRecipient: require('mail/static/src/components/composer_suggested_recipient_info/composer_suggested_recipient_info.js'),
};

class ComposerSuggestedRecipientsList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            isShowMore: false
        });

        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                thread: thread ? thread.__state : undefined,
            };
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
        this.state.isShowMore = false;
    }

    /**
     * @private
     */
    _onClickShowMore(ev) {
        this.state.isShowMore = true;
    }

}

Object.assign(ComposerSuggestedRecipientsList, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.ComposerSuggestedRecipientsList',
});

return ComposerSuggestedRecipientsList;
});
