odoo.define('mail/static/src/components/thread_icon/thread_icon.js', function (require) {
'use strict';

const components = {
    ThreadTypingIcon: require('mail/static/src/components/thread_typing_icon/thread_typing_icon.js'),
};
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class ThreadIcon extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            const correspondent = thread ? thread.correspondent : undefined;
            return {
                correspondent,
                correspondentImStatus: correspondent && correspondent.im_status,
                history: this.env.messaging.history,
                inbox: this.env.messaging.inbox,
                moderation: this.env.messaging.moderation,
                partnerRoot: this.env.messaging.partnerRoot,
                starred: this.env.messaging.starred,
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
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

}

Object.assign(ThreadIcon, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.ThreadIcon',
});

return ThreadIcon;

});
