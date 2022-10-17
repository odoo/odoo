/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { useService } from "@web/core/utils/hooks";
import { FormViewDialog } from '@web/views/view_dialogs/form_view_dialog';

const { Component } = owl;

export class ComposerSuggestedRecipient extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'checkboxRef', refName: 'checkbox' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
        this.dialogService = useService("dialog");
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ComposerSuggestedRecipientView}
     */
    get composerSuggestedRecipientView() {
        return this.props.record;
    }

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onChangeCheckbox() {
        if (!this.composerSuggestedRecipientView.exists()) {
            return;
        }
        const isChecked = this.composerSuggestedRecipientView.checkboxRef.el.checked;
        this.composerSuggestedRecipientView.suggestedRecipientInfo.update({ isSelected: isChecked });
        if (!this.composerSuggestedRecipientView.suggestedRecipientInfo.partner) {
            // Recipients must always be partners. On selecting a suggested
            // recipient that does not have a partner, the partner creation form
            // should be opened.
            if (isChecked) {
                this.dialogService.add(FormViewDialog, {
                    context: {
                        active_id: this.composerSuggestedRecipientView.suggestedRecipientInfo.thread.id,
                        active_model: 'mail.compose.message',
                        default_email: this.composerSuggestedRecipientView.suggestedRecipientInfo.email,
                        default_name: this.composerSuggestedRecipientView.suggestedRecipientInfo.name,
                        default_lang: this.composerSuggestedRecipientView.suggestedRecipientInfo.lang,
                        force_email: true,
                        ref: 'compound_context',
                    },
                    onRecordSaved: () => this.composerSuggestedRecipientView.onDialogSaved(),
                    resModel: "res.partner",
                    title: this.composerSuggestedRecipientView.suggestedRecipientInfo.dialogText,
                });
            }
        }
    }

}

Object.assign(ComposerSuggestedRecipient, {
    props: { record: Object },
    template: 'mail.ComposerSuggestedRecipient',
});

registerMessagingComponent(ComposerSuggestedRecipient);
