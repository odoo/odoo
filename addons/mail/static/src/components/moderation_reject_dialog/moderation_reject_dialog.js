odoo.define('mail/static/src/components/moderation_reject_dialog/moderation_reject_dialog.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const components = {
    Dialog: require('web.OwlDialog'),
};

const { Component, useState } = owl;
const { useRef } = owl.hooks;

class ModerationRejectDialog extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this.state = useState({
            title: this.env._t("Message Rejected"),
            comment: this.env._t("Your message was rejected by moderator."),
        });
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
    get SEND_EXPLANATION_TO_AUTHOR() {
        return this.env._t("Send explanation to author");
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
    _onClickReject() {
        this._dialogRef.comp._close();
        const kwargs = {
            title: this.state.title,
            comment: this.state.comment,
        };
        this.env.models['mail.message'].moderate(this.messages, 'reject', kwargs);
    }

}

Object.assign(ModerationRejectDialog, {
    components,
    props: {
        messageLocalIds: {
            type: Array,
            element: String,
        },
    },
    template: 'mail.ModerationRejectDialog',
});

return ModerationRejectDialog;

});
