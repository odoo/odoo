/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Dialog from 'web.OwlDialog';

const { Component } = owl;

class SnailmailError extends Component {
    setup() {
        this.dialogAPI = {};
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {boolean}
     */
    get hasCreditsError() {
        return (
            this.notification.failure_type === 'sn_credit' ||
            this.notification.failure_type === 'sn_trial'
        );
    }

    /**
     * @returns {Message}
     */
    get message() {
        return this.messaging && this.messaging.models['Message'].get(this.props.messageLocalId);
    }

    /**
     * @returns {Notification}
     */
    get notification() {
        // Messages from snailmail are considered to have at most one notification.
        return this.message.notifications[0];
    }

    /**
     * @returns {string}
     */
    get title() {
        return this.env._t("Failed letter");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickCancelLetter() {
        this.dialogAPI.close();
        this.message.cancelLetter();
    }

    /**
     * @private
     */
    _onClickClose() {
        this.dialogAPI.close();
    }

    /**
     * @private
     */
    _onClickResendLetter() {
        this.dialogAPI.close();
        this.message.resendLetter();
    }

}

Object.assign(SnailmailError, {
    components: { Dialog },
    props: {
        messageLocalId: String,
        onClosed: {
            type: Function,
            optional: true,
        },
    },
    template: 'snailmail.SnailmailError',
});

registerMessagingComponent(SnailmailError);

export default SnailmailError;
