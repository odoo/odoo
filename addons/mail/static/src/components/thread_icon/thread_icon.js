/** @odoo-module **/

import { useShouldUpdateBasedOnProps } from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import { useStore } from '@mail/component_hooks/use_store/use_store';
import { ThreadTypingIcon } from '@mail/components/thread_typing_icon/thread_typing_icon';

const { Component } = owl;

const components = { ThreadTypingIcon };

export class ThreadIcon extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const thread = this.env.services.messaging.models['mail.thread'].get(props.threadLocalId);
            const correspondent = thread ? thread.correspondent : undefined;
            return {
                correspondent,
                correspondentImStatus: correspondent && correspondent.im_status,
                history: this.env.services.messaging.messaging.history,
                inbox: this.env.services.messaging.messaging.inbox,
                partnerRoot: this.env.services.messaging.messaging.partnerRoot,
                starred: this.env.services.messaging.messaging.starred,
                thread,
                threadChannelType: thread && thread.channel_type,
                threadModel: thread && thread.model,
                threadOrderedOtherTypingMembersLength: thread && thread.orderedOtherTypingMembers.length,
                threadPublic: thread && thread.public,
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
        return this.env.services.messaging.models['mail.thread'].get(this.props.threadLocalId);
    }

}

Object.assign(ThreadIcon, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadIcon',
});
