/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { FormViewDialog } from 'web.view_dialogs';
import { ComponentAdapter } from 'web.OwlCompatibility';

const { Component, useRef } = owl;

class FormViewDialogComponentAdapter extends ComponentAdapter {

    async renderWidget() {
        // Ensure the dialog is properly reconstructed. Without this line, it is
        // impossible to open the dialog again after having it closed a first
        // time, because the DOM of the dialog has disappeared.
        await this.onWillStart();
        this.props.setFormViewDialogWidget(this.widget);
    }

    updateWidget() {
        // This component should never be re-rendered but because shouldUpdate was removed,
        // when the Composer is rerendered, so is the ComposerSuggestedRecipients even
        // though its props haven't changed and there is nothing to do.
    }

    get widgetArgs() {
        return [this.props.params];
    }
}

export class ComposerSuggestedRecipient extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        this.id = _.uniqueId('o_ComposerSuggestedRecipient_');
        useUpdate({ func: () => this._update() });
        /**
         * Form view dialog class. Useful to reference it in the template.
         */
        this.FormViewDialog = FormViewDialog;
        /**
         * Reference of the checkbox. Useful to know whether it was checked or
         * not, to properly update the corresponding state in the record or to
         * prompt the user with the partner creation dialog.
         */
        this._checkboxRef = useRef('checkbox');
        /**
         * Reference of the partner creation dialog. Useful to open it, for
         * compatibility with old code.
         */
        this.setFormViewDialogWidget = (widget) => {
            this._dialogWidget = widget;
        };
        /**
         * Whether the dialog is currently open. `_dialogRef` cannot be trusted
         * to know if the dialog is open due to manually calling `open` and
         * potential out of sync with component adapter.
         */
        this._isDialogOpen = false;
        this._onDialogSaved = this._onDialogSaved.bind(this);
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
            if (isChecked && this._dialogWidget && !this._isDialogOpen) {
                this._isDialogOpen = true;
                this._dialogWidget.on('closed', this, () => {
                    this._isDialogOpen = false;
                });
                this._dialogWidget.open();
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
    components: { FormViewDialogComponentAdapter },
    props: { record: Object },
    template: 'mail.ComposerSuggestedRecipient',
});

registerMessagingComponent(ComposerSuggestedRecipient);
