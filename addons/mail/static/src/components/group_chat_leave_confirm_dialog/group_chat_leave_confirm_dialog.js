/** @odoo-module **/

import useShouldUpdateBasedOnProps from '@mail/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props';
import useStore from '@mail/component_hooks/use_store/use_store';
import Dialog from 'web.OwlDialog';

const components = { Dialog };

const { Component } = owl;
const { useRef } = owl.hooks;

class GroupChatLeaveConfirmDialog extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
        useStore(props => {
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                thread: thread ? thread.__state : undefined,
            };
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
        return _.str.sprintf(
            this.env._t(`You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?`)
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
    _onClickOk() {
        this._dialogRef.comp._close();
        this.thread.unsubscribe();
    }

}

Object.assign(GroupChatLeaveConfirmDialog, {
    components,
    props: {
        threadLocalId: String,
    },
    template: 'mail.GroupChatLeaveConfirmDialog',
});

export default GroupChatLeaveConfirmDialog;
