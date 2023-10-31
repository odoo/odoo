/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { markEventHandled } from '@mail/utils/utils';

const { Component } = owl;

export class EditableText extends Component {

    mounted() {
        this.el.focus();
        this.el.setSelectionRange(0, (this.el.value && this.el.value.length) || 0);
    }

    willUnmount() {
        this.trigger('o-cancel');
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onBlur(ev) {
        this.trigger('o-cancel');
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        markEventHandled(ev, 'EditableText.click');
        this.trigger('o-clicked');
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        switch (ev.key) {
            case 'Enter':
                this._onKeydownEnter(ev);
                break;
            case 'Escape':
                this.trigger('o-cancel');
                break;
        }
    }

    /**
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydownEnter(ev) {
        if (!this.el) {
            return;
        }
        const value = this.el.value;
        const newName = value || this.props.placeholder;
        if (this.props.value !== newName) {
            this.trigger('o-validate', { newName });
        } else {
            this.trigger('o-cancel');
        }
    }

}

Object.assign(EditableText, {
    defaultProps: {
        placeholder: "",
        value: "",
    },
    props: {
        placeholder: String,
        value: String,
    },
    template: 'mail.EditableText',
});

registerMessagingComponent(EditableText);
