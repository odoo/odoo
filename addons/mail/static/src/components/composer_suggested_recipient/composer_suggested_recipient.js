/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { FormViewDialog } from 'web.view_dialogs';
import { standaloneAdapter } from 'web.OwlCompatibility';
import session from 'web.session';

const { Component, useRef } = owl;

export class ComposerSuggestedRecipient extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.id = _.uniqueId('o_ComposerSuggestedRecipient_');
        useUpdate({ func: () => this._update() });
        /**
         * Reference of the checkbox. Useful to know whether it was checked or
         * not, to properly update the corresponding state in the record or to
         * prompt the user with the partner creation dialog.
         */
        this._checkboxRef = useRef('checkbox');
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {SuggestedRecipientInfo}
     */
    get suggestedRecipientInfo() {
        return this.messaging && this.messaging.models['SuggestedRecipientInfo'].get(this.props.suggestedRecipientInfoLocalId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        if (this._checkboxRef.el && this.suggestedRecipientInfo) {
            this._checkboxRef.el.checked = this.suggestedRecipientInfo.isSelected;
        }
    }

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onChangeCheckbox() {
        const isChecked = this._checkboxRef.el.checked;
        this.suggestedRecipientInfo.update({ isSelected: isChecked });
        if (!this.suggestedRecipientInfo.partner) {
            // Recipients must always be partners. On selecting a suggested
            // recipient that does not have a partner, the partner creation form
            // should be opened.
            if (isChecked) {
                const adapterParent = standaloneAdapter({ Component });
                const selectCreateDialog = new FormViewDialog(adapterParent, {
                    context: {
                        ...session.user_context,
                        active_id: this.suggestedRecipientInfo.thread.id,
                        active_model: 'mail.compose.message',
                        default_email: this.suggestedRecipientInfo.email,
                        default_name: this.suggestedRecipientInfo.name,
                        default_lang: this.suggestedRecipientInfo.lang,
                        force_email: true,
                        ref: 'compound_context',
                    },
                    disable_multiple_selection: true,
                    on_saved: this._onDialogSaved.bind(this),
                    res_id: false,
                    res_model: 'res.partner',
                    title: this.suggestedRecipientInfo.dialogText,
                });
                selectCreateDialog.open();
            }
        }
    }

    /**
     * @private
     * @param {object} record the newly-created record
     */
    _onDialogSaved(record) {
        const thread = this.suggestedRecipientInfo && this.suggestedRecipientInfo.thread;
        if (!thread) {
            return;
        }
        thread.fetchData(['suggestedRecipients']);
        if (!this.suggestedRecipientInfo.partner) {
            this.env.services.notification.notify({
                title: this.env._t('Invalid Partner'),
                message: this.env._t('The information you have entered does not match the existing contact information for this record. The partner was not created.'),
                type: 'warning'
            });
            this.env.services.rpc({
                args: [record.res_id],
                model: 'res.partner',
                method: 'unlink',
            });
        }
    }
}

Object.assign(ComposerSuggestedRecipient, {
    props: {
        suggestedRecipientInfoLocalId: String,
    },
    template: 'mail.ComposerSuggestedRecipient',
});

registerMessagingComponent(ComposerSuggestedRecipient);
