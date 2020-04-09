odoo.define('mail.messaging.component.ModerationBanDialog', function (require) {
'use strict';

const useStore = require('mail.messaging.component_hook.useStore');

const Dialog = require('web.OwlDialog');

const { Component } = owl;
const { useRef } = owl.hooks;

class ModerationBanDialog extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            return {
                messages: props.messageLocalIds.map(localId => this.env.entities.Message.get(localId)),
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
     * @returns {mail.messaging.entity.Message[]}
     */
    get messages() {
        return this.props.messageLocalIds.map(localId => this.env.entities.Message.get(localId));
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickBan() {
        this._dialogRef.comp._close();
        this.env.entities.Message.moderate(this.messages, 'ban');
    }

    /**
     * @private
     */
    _onClickCancel() {
        this._dialogRef.comp._close();
    }

}

Object.assign(ModerationBanDialog, {
    components: { Dialog },
    props: {
        messageLocalIds: {
            type: Array,
            element: String,
        },
    },
    template: 'mail.messaging.component.ModerationBanDialog',
});

return ModerationBanDialog;

});
