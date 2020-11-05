odoo.define('mail/static/src/components/message_delete_confirm_dialog/message_delete_confirm_dialog.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const components = {
    Dialog: require('web.OwlDialog'),
    Message: require('mail/static/src/components/message/message.js'),
};

const { Component, QWeb } = owl;
const { useRef } = owl.hooks;

class MessageDeleteConfirmDialog extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const message = this.env.models['mail.message'].get(props.messageLocalId);
            return {
                message: message ? message.__state : undefined,
            };
        });
        // to manually trigger the dialog close event
        this._dialogRef = useRef('dialog');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.attachment}
     */
    get message() {
        return this.env.models['mail.message'].get(this.props.messageLocalId);
    }

    /**
     * @returns {string}
     */
    getBody() {
        // if (this.message.originThread.model != 'mail.channel') {
        return this.env._t("Are you sure you want to delete this message?");
    }

    /**
     * @returns {string}
     */
    getTitle() {
        return this.env._t("Confirmation");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickCancel() {
        this._dialogRef.comp._close();
    }

    /**
     * @private
     */
    _onClickOk() {
        this._dialogRef.comp._close();
        this.message.deleteServerRecord();
        this.trigger('o-message-removed', { messageLocalId: this.props.messageLocalId });
    }

}

Object.assign(MessageDeleteConfirmDialog, {
    components,
    props: {
        messageLocalId: String,
    },
    template: 'mail.MessageDeleteConfirmDialog',
});

QWeb.registerComponent('MessageDeleteConfirmDialog', MessageDeleteConfirmDialog);

return MessageDeleteConfirmDialog;

});
