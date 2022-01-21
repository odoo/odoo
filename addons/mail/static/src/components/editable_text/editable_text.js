odoo.define('mail/static/src/components/editable_text/editable_text.js', function (require) {
'use strict';

const { markEventHandled } = require('mail/static/src/utils/utils.js');
const useShouldUpdateBasedOnProps = require('mail/static/src/component_hooks/use_should_update_based_on_props/use_should_update_based_on_props.js');

const { Component } = owl;

class EditableText extends Component {

    constructor(...args) {
        super(...args);
        useShouldUpdateBasedOnProps();
    }

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

return EditableText;

});
