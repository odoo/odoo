odoo.define('snailmail/static/src/components/snailmail_error_dialog/snailmail_error_dialog.js', function (require) {
'use strict';

const { useModels } = require('@mail/component_hooks/use_models/use_models');
const { useShouldUpdateBasedOnProps } = require('@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props');

const Dialog = require('web.OwlDialog');

const { Component } = owl;
const { useRef } = owl.hooks;

class SnailmailErrorDialog extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
        useShouldUpdateBasedOnProps();
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
        return this.env.models['mail.message'].get(this.props.messageLocalId);
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

return SnailmailErrorDialog;

});
