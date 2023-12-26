odoo.define('mail/static/src/components/thread_textual_typing_status/thread_textual_typing_status.js', function (require) {
'use strict';

const components = {
    ThreadTypingIcon: require('mail/static/src/components/thread_typing_icon/thread_typing_icon.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class ThreadTextualTypingStatus extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                threadOrderedOtherTypingMembersLength: thread && thread.orderedOtherTypingMembersLength,
                threadTypingStatusText: thread && thread.typingStatusText,
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

}

Object.assign(ThreadTextualTypingStatus, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadTextualTypingStatus',
});

return ThreadTextualTypingStatus;

});
