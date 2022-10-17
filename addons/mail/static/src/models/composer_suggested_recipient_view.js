/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';

registerModel({
    name: 'ComposerSuggestedRecipientView',
    recordMethods: {
        onChangeCheckbox() {
            if (!this.exists()) {
                return;
            }
            const isChecked = this.checkboxRef.el.checked;
            this.suggestedRecipientInfo.update({ isSelected: isChecked });
            if (!this.suggestedRecipientInfo.partner) {
                // Recipients must always be partners. On selecting a suggested
                // recipient that does not have a partner, the partner creation form
                // should be opened.
                if (isChecked) {
                    this.env.services.dialog.add(FormViewDialog, {
                        context: {
                            active_id: this.suggestedRecipientInfo.thread.id,
                            active_model: 'mail.compose.message',
                            default_email: this.suggestedRecipientInfo.email,
                            default_name: this.suggestedRecipientInfo.name,
                            default_lang: this.suggestedRecipientInfo.lang,
                            force_email: true,
                            ref: 'compound_context',
                        },
                        onRecordSaved: () => this.onDialogSaved(),
                        resModel: "res.partner",
                        title: this.suggestedRecipientInfo.dialogText,
                    });
                }
            }
        },
        onComponentUpdate() {
            if (this.checkboxRef.el && this.suggestedRecipientInfo) {
                this.checkboxRef.el.checked = this.suggestedRecipientInfo.isSelected;
            }
        },
        onDialogSaved() {
            if (!this.exists()) {
                return;
            }
            const thread = (
                this.suggestedRecipientInfo &&
                this.suggestedRecipientInfo.thread
            );
            if (!thread) {
                return;
            }
            thread.fetchData(['suggestedRecipients']);
        },
    },
    fields: {
        /**
         * Reference of the checkbox. Useful to know whether it was checked or
         * not, to properly update the corresponding state in the record or to
         * prompt the user with the partner creation dialog.
         */
        checkboxRef: attr(),
        composerSuggestedRecipientListViewOwner: one('ComposerSuggestedRecipientListView', {
            identifying: true,
            inverse: 'composerSuggestedRecipientViews',
        }),
        suggestedRecipientInfo: one('SuggestedRecipientInfo', {
            identifying: true,
            inverse: 'composerSuggestedRecipientViews',
        }),
    },
});
