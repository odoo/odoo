/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Dialog from 'web.OwlDialog';

const { Component } = owl;
const { useRef } = owl.hooks;

class SnailmailErrorDialog extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        // to manually trigger the dialog close event
        this._dialogRef = useRef('dialog');
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
     * @returns {mail.message}
     */
    get message() {
        return this.messaging && this.messaging.models['mail.message'].get(this.props.messageLocalId);
    }

    /**
     * @returns {mail.notification}
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
        this._dialogRef.comp._close();
        this.message.cancelLetter();
    }

    /**
     * @private
     */
    _onClickClose() {
        this._dialogRef.comp._close();
    }

    /**
     * @private
     */
    _onClickResendLetter() {
        this._dialogRef.comp._close();
        this.message.resendLetter();
    }

}

Object.assign(SnailmailErrorDialog, {
    components: { Dialog },
    props: {
        messageLocalId: String,
    },
    template: 'snailmail.SnailmailErrorDialog',
});

registerMessagingComponent(SnailmailErrorDialog);

export default SnailmailErrorDialog;
