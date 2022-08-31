/** @odoo-module **/

import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

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
        // handled in mail/static/src/backend_components/composer_suggested_recipient/composer_suggested_recipient.js
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
