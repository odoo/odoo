odoo.define('mail.component.EditableText', function () {
'use strict';

class EditableText extends owl.Component {

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
        const value = this.el.value;
        const newName = value || this.props.placeholder;
        if (this.props.value !== newName) {
            this.trigger('o-validate', {
                newName: newName,
            });
        } else {
            this.trigger('o-cancel');
        }
    }
}

/**
 * Props validation
 */
EditableText.props = {
    placeholder: String,
    value: String,
};

EditableText.defaultProps = {
    placeholder: "",
    value: "",
};

EditableText.template = 'mail.component.EditableText';

return EditableText;

});
