odoo.define('mail.component.MessageAuthorPrefix', function () {
'use strict';

const { Component } = owl;
const { useGetters, useStore } = owl.hooks;

class MessageAuthorPrefix extends Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeGetters = useGetters();
        this.storeProps = useStore((state, props) => {
            const message = state.messages[props.messageLocalId];
            const author = state.partners[message.authorLocalId];
            const thread = props.threadLocalId
                ? state.threads[props.threadLocalId]
                : undefined;
            return {
                author,
                authorName: author
                    ? this.storeGetters.partnerName(author.localId)
                    : undefined,
                currentPartnerLocalId: state.currentPartnerLocalId,
                thread,
            };
        });
    }
}

MessageAuthorPrefix.props = {
    messageLocalId: String,
    threadLocalId: {
        type: String,
        optional: true,
    },
};

MessageAuthorPrefix.template = 'mail.component.MessageAuthorPrefix';

return MessageAuthorPrefix;

});
