odoo.define('mail/static/src/components/moderation_ban_dialog/moderation_ban_dialog.js', function (require) {
'use strict';

const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');
const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');

const components = {
    Dialog: require('web.OwlDialog'),
};

const { Component } = owl;
const { useRef } = owl.hooks;

class ModerationBanDialog extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps({
            compareDepth: {
                messageLocalIds: 1,
            },
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
        return this.props.messageLocalIds.map(localId => this.env.models['mail.message'].get(localId));
    }

    /**
     * @returns {string}
     */
    get CONFIRMATION() {
        return this.env._t("Confirmation");
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickBan() {
        this._dialogRef.comp._close();
        this.env.models['mail.message'].moderate(this.messages, 'ban');
    }

    /**
     * @private
     */
    _onClickCancel() {
        this._dialogRef.comp._close();
    }

}

Object.assign(ModerationBanDialog, {
    components,
    props: {
        messageLocalIds: {
            type: Array,
            element: String,
        },
    },
    template: 'mail.ModerationBanDialog',
});

return ModerationBanDialog;

});
