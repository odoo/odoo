/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import ThreadTypingIcon from '@mail/components/thread_typing_icon/thread_typing_icon';

const { Component } = owl;

const components = { ThreadTypingIcon };

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

export default ThreadTextualTypingStatus;
