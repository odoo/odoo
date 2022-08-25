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
     * @returns {ComposerSuggestedRecipientView}
     */
    get composerSuggestedRecipientView() {
        return this.props.record;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _update() {
        if (this._checkboxRef.el && this.composerSuggestedRecipientView.suggestedRecipientInfo) {
            this._checkboxRef.el.checked = this.composerSuggestedRecipientView.suggestedRecipientInfo.isSelected;
        }
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
    }

    /**
     * @private
     */
    _onDialogSaved() {
        if (!this.composerSuggestedRecipientView.exists()) {
            return;
        }
        const thread = (
            this.composerSuggestedRecipientView.suggestedRecipientInfo &&
            this.composerSuggestedRecipientView.suggestedRecipientInfo.thread
        );
        if (!thread) {
            return;
        }
        thread.fetchData(['suggestedRecipients']);
    }
}

Object.assign(ComposerSuggestedRecipient, {
    props: { record: Object },
    template: 'mail.ComposerSuggestedRecipient',
});

registerMessagingComponent(ComposerSuggestedRecipient);
