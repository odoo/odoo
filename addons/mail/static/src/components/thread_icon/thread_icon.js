odoo.define('mail/static/src/components/thread_icon/thread_icon.js', function (require) {
'use strict';

const components = {
    ThreadTypingIcon: require('mail/static/src/components/thread_typing_icon/thread_typing_icon.js'),
};
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class ThreadIcon extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            const correspondent = thread ? thread.correspondent : undefined;
            return {
                correspondent: correspondent ? correspondent.__state : undefined,
                partnerRoot: this.env.messaging.partnerRoot
                    ? this.env.messaging.partnerRoot.__state
                    : undefined,
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
