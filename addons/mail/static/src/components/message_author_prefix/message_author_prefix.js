odoo.define('mail/static/src/components/message_author_prefix/message_author_prefix.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class MessageAuthorPrefix extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const message = this.env.models['mail.message'].get(props.messageLocalId);
            const author = message ? message.author : undefined;
            const thread = props.threadLocalId
                ? this.env.models['mail.thread'].get(props.threadLocalId)
                : undefined;
            return {
                author: author ? author.__state : undefined,
                currentPartner: this.env.messaging.currentPartner
                    ? this.env.messaging.currentPartner.__state
                    : undefined,
                message: message ? message.__state : undefined,
                thread: thread ? thread.__state : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.message}
     */
    get message() {
        return this.env.models['mail.message'].get(this.props.messageLocalId);
    }

    /**
     * @returns {mail.thread|undefined}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

}

Object.assign(MessageAuthorPrefix, {
    props: {
        messageLocalId: String,
        threadLocalId: {
            type: String,
            optional: true,
        },
    },
    template: 'mail.MessageAuthorPrefix',
});

return MessageAuthorPrefix;

});
