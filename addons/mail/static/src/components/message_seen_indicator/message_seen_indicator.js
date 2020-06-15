odoo.define('mail/static/src/components/message_seen_indicator/message_seen_indicator.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const { Component } = owl;

class MessageSeenIndicator extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const message = this.env.models['mail.message'].get(props.messageLocalId);
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            const messageSeenIndicator = this.env.models['mail.message_seen_indicator'].find(
                messageSeenIndicator =>
                    messageSeenIndicator.message === message &&
                    messageSeenIndicator.thread === thread
            );
            return {
                messageSeenIndicator: messageSeenIndicator ? messageSeenIndicator.__state : undefined,
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {string}
     */
    get indicatorTitle() {
        if (!this.messageSeenIndicator) {
            return '';
        }
        if (this.messageSeenIndicator.hasEveryoneSeen) {
            return this.env._t("Seen by Everyone");
        }
        if (this.messageSeenIndicator.hasSomeoneSeen) {
            const partnersThatHaveSeen = this.messageSeenIndicator.partnersThatHaveSeen.map(
                partner => partner.name
            );
            if (partnersThatHaveSeen.length === 1) {
                return _.str.sprintf(
                    this.env._t("Seen by %s"),
                    partnersThatHaveSeen[0]
                );
            }
            if (partnersThatHaveSeen.length === 2) {
                return _.str.sprintf(
                    this.env._t("Seen by %s and %s"),
                    partnersThatHaveSeen[0],
                    partnersThatHaveSeen[1]
                );
            }
            return _.str.sprintf(
                this.env._t("Seen by %s, %s and more"),
                partnersThatHaveSeen[0],
                partnersThatHaveSeen[1]
            );
        }
        if (this.messageSeenIndicator.hasEveryoneFetched) {
            return this.env._t("Received by Everyone");
        }
        if (this.messageSeenIndicator.hasSomeoneFetched) {
            const partnersThatHaveFetched = this.messageSeenIndicator.partnersThatHaveFetched.map(
                partner => partner.name
            );
            if (partnersThatHaveFetched.length === 1) {
                return _.str.sprintf(
                    this.env._t("Received by %s"),
                    partnersThatHaveFetched[0]
                );
            }
            if (partnersThatHaveFetched.length === 2) {
                return _.str.sprintf(
                    this.env._t("Received by %s and %s"),
                    partnersThatHaveFetched[0],
                    partnersThatHaveFetched[1]
                );
            }
            return _.str.sprintf(
                this.env._t("Received by %s, %s and more"),
                partnersThatHaveFetched[0],
                partnersThatHaveFetched[1]
            );
        }
        return '';
    }

    /**
     * @returns {mail.message}
     */
    get message() {
        return this.env.models['mail.message'].get(this.props.messageLocalId);
    }

    /**
     * @returns {mail.message_seen_indicator}
     */
    get messageSeenIndicator() {
        return this.env.models['mail.message_seen_indicator'].find(messageSeenIndicator =>
            messageSeenIndicator.message === this.message &&
            messageSeenIndicator.thread === this.thread
        );
    }

    /**
     * @returns {mail.Thread}
     */
    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }
}

Object.assign(MessageSeenIndicator, {
    props: {
        messageLocalId: String,
        threadLocalId: String,
    },
    template: 'mail.MessageSeenIndicator',
});

return MessageSeenIndicator;

});
