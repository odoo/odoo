/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { useUpdate } from '@mail/component_hooks/use_update';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ComposerTextInput extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'mirroredTextareaRef', modelName: 'ComposerView', refName: 'mirroredTextarea' });
        useRefToModel({ fieldName: 'textareaRef', modelName: 'ComposerView', refName: 'textarea' });
        /**
         * Updates the composer text input content when composer is mounted
         * as textarea content can't be changed from the DOM.
         */
        useUpdate({ func: () => this._update() });
        /**
         * Last content of textarea from input event. Useful to determine
         * whether the current partner is typing something.
         */
        this._textareaLastInputValue = "";
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ComposerView}
     */
    get composerView() {
        return this.messaging && this.messaging.models['ComposerView'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Determines whether the textarea is empty or not.
     *
     * @private
     * @returns {boolean}
     */
    _isEmpty() {
        return this.composerView.textareaRef.el.value === "";
    }

    /**
     * Updates the content and height of a textarea
     *
     * @private
     */
    _update() {
        if (!this.composerView) {
            return;
        }
        if (!this.root.el) {
            return;
        }
        if (this.composerView.doFocus) {
            this.composerView.update({ doFocus: false });
            if (this.messaging.device.isSmall) {
                this.root.el.scrollIntoView();
            }
            this.composerView.textareaRef.el.focus();
        }
        if (this.composerView.hasToRestoreContent) {
            this.composerView.textareaRef.el.value = this.composerView.composer.textInputContent;
            if (this.composerView.isFocused) {
                this.composerView.textareaRef.el.setSelectionRange(
                    this.composerView.composer.textInputCursorStart,
                    this.composerView.composer.textInputCursorEnd,
                    this.composerView.composer.textInputSelectionDirection,
                );
            }
            this.composerView.update({ hasToRestoreContent: false });
        }
        this._updateHeight();
    }

    /**
     * Updates the textarea height.
     *
     * @private
     */
    _updateHeight() {
        this.composerView.mirroredTextareaRef.el.value = this.composerView.composer.textInputContent;
        this.composerView.textareaRef.el.style.height = this.composerView.mirroredTextareaRef.el.scrollHeight + 'px';
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onInputTextarea() {
        if (!this.composerView) {
            return;
        }
        this.composerView.saveStateInStore();
        if (this._textareaLastInputValue !== this.composerView.textareaRef.el.value) {
            this.composerView.handleCurrentPartnerIsTyping();
        }
        this._textareaLastInputValue = this.composerView.textareaRef.el.value;
        this._updateHeight();
    }

}

Object.assign(ComposerTextInput, {
    props: { localId: String },
    template: 'mail.ComposerTextInput',
});

registerMessagingComponent(ComposerTextInput);
