odoo.define('mail/static/src/components/message_seen_indicator/message_seen_indicator.js', function (require) {
'use strict';

const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;

class MessageSeenIndicator extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
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
        if (this.messageSeenIndicator.__mfield_hasEveryoneSeen(this)) {
            return this.env._t("Seen by Everyone");
        }
        if (this.messageSeenIndicator.__mfield_hasSomeoneSeen(this)) {
            const partnersThatHaveSeen = this.messageSeenIndicator.__mfield_partnersThatHaveSeen(this).map(
                partner => partner.__mfield_name(this)
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
        if (this.messageSeenIndicator.__mfield_hasEveryoneFetched(this)) {
            return this.env._t("Received by Everyone");
        }
        if (this.messageSeenIndicator.__mfield_hasSomeoneFetched(this)) {
            const partnersThatHaveFetched = this.messageSeenIndicator.__mfield_partnersThatHaveFetched(this).map(
                partner => partner.__mfield_name(this)
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
            messageSeenIndicator.__mfield_message() === this.message &&
            messageSeenIndicator.__mfield_thread() === this.thread
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
