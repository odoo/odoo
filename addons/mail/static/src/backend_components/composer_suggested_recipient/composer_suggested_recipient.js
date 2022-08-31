/** @odoo-module **/

import { ComposerSuggestedRecipient } from '@mail/components/composer_suggested_recipient/composer_suggested_recipient';

import { standaloneAdapter } from 'web.OwlCompatibility';
import session from 'web.session';
import { patch } from 'web.utils';
import { FormViewDialog } from 'web.view_dialogs';

const { Component } = owl;

patch(ComposerSuggestedRecipient.prototype, 'mail/static/src/backend_components/composer_suggested_recipient/composer_suggested_recipient.js', {
    /**
     * @private
     */
     _onChangeCheckbox() {
        if (!this.composerSuggestedRecipientView.exists()) {
            return;
        }
        const isChecked = this._checkboxRef.el.checked;
        this.composerSuggestedRecipientView.suggestedRecipientInfo.update({ isSelected: isChecked });
        if (!this.composerSuggestedRecipientView.suggestedRecipientInfo.partner) {
            // Recipients must always be partners. On selecting a suggested
            // recipient that does not have a partner, the partner creation form
            // should be opened.
            if (isChecked) {
                const adapterParent = standaloneAdapter({ Component });
                const selectCreateDialog = new FormViewDialog(adapterParent, {
                    context: {
                        ...session.user_context,
                        active_id: this.composerSuggestedRecipientView.suggestedRecipientInfo.thread.id,
                        active_model: 'mail.compose.message',
                        default_email: this.composerSuggestedRecipientView.suggestedRecipientInfo.email,
                        default_name: this.composerSuggestedRecipientView.suggestedRecipientInfo.name,
                        default_lang: this.composerSuggestedRecipientView.suggestedRecipientInfo.lang,
                        force_email: true,
                        ref: 'compound_context',
                    },
                    disable_multiple_selection: true,
                    on_saved: this._onDialogSaved.bind(this),
                    res_id: false,
                    res_model: 'res.partner',
                    title: this.composerSuggestedRecipientView.suggestedRecipientInfo.dialogText,
                });
                selectCreateDialog.open();
            }
        }
    },
});
