/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';

import Dialog from 'web.OwlDialog';

const { Component } = owl;
const { useRef } = owl.hooks;

const components = { Dialog };

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

export default ModerationBanDialog;
