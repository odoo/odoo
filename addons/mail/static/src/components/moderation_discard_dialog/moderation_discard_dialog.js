odoo.define('mail/static/src/components/moderation_discard_dialog/moderation_discard_dialog.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const components = {
    Dialog: require('web.OwlDialog'),
};

const { Component } = owl;
const { useRef } = owl.hooks;

class ModerationDiscardDialog extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            const messages = props.messageLocalIds.map(localId =>
                this.env.models['mail.message'].get(localId)
            );
            return {
                messages: messages.map(message => message ? message.__state : undefined),
            };
        }, {
            compareDepth: {
                messages: 1,
            },
        });
        // to manually trigger the dialog close event
        this._dialogRef = useRef('dialog');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {string}
     */
    getBody() {
        if (this.messages.length === 1) {
            return this.env._t("You are going to discard 1 message.");
        }
        return _.str.sprintf(
            this.env._t("You are going to discard %s messages."),
            this.messages.length
        );
    }

    /**
     * @returns {mail.message[]}
     */
    get messages() {
        return this.props.messageLocalIds.map(localId =>
            this.env.models['mail.message'].get(localId)
        );
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
    _onClickDiscard() {
        this._dialogRef.comp._close();
        this.env.models['mail.message'].moderate(this.messages, 'discard');
    }

}

Object.assign(ModerationDiscardDialog, {
    components,
    props: {
        messageLocalIds: {
            type: Array,
            element: String,
        },
    },
    template: 'mail.ModerationDiscardDialog',
});

return ModerationDiscardDialog;

});
