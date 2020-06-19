odoo.define('web.basic_fields_owl', function (require) {
    "use strict";

    const AbstractField = require('web.AbstractFieldOwl');
    const CustomCheckbox = require('web.CustomCheckbox');
    const { _lt } = require('web.translation');


    /**
     * FieldBadge displays the field's value inside a bootstrap pill badge.
     * The supported field's types are 'char', 'selection' and 'many2one'.
     *
     * By default, the background color of the badge is a light gray, but it can
     * be customized by setting a 'decoration-xxx' attribute on the field.
     * For instance,
     *   <field name="some_field" widget="badge" decoration-danger="state == 'cancel'"/>
     * renders a badge with a red background on records matching the condition.
     */
    class FieldBadge extends AbstractField {
        _getClassFromDecoration(decoration) {
            return `bg-${decoration.split('-')[1]}-light`;
        }
    }
    FieldBadge.description = _lt("Badge");
    FieldBadge.supportedFieldTypes = ['selection', 'many2one', 'char'];
    FieldBadge.template = 'web.FieldBadge';


    class FieldBoolean extends AbstractField {
        patched() {
            super.patched();
            if (this.props.event && this.props.event.target === this) {
                this.activate();
            }
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @override
         * @returns {HTMLElement|null} the focusable checkbox input
         */
        get focusableElement() {
            return this.mode === 'readonly' ? null : this.el.querySelector('input');
        }
        /**
         * A boolean field is always set since false is a valid value.
         *
         * @override
         */
        get isSet() {
            return true;
        }
        /**
         * Toggle the checkbox if it is activated due to a click on itself.
         *
         * @override
         * @param {Object} [options]
         * @param {Event} [options.event] the event which fired this activation
         * @returns {boolean} true if the component was activated, false if the
         *                    focusable element was not found or invisible
         */
        activate(options) {
            const activated = super.activate(options);
            // The event might have been fired on the non field version of
            // this field, we can still test the presence of its custom class.
            if (activated && options && options.event && options.event.target
                .closest('.custom-control.custom-checkbox')) {
                this._setValue(!this.value);  // Toggle the checkbox
            }
            return activated;
        }
        /**
         * Associates the 'for' attribute of the internal label.
         *
         * @override
         */
        setIdForLabel(id) {
            super.setIdForLabel(id);
            this.el.querySelector('label').setAttribute('for', id);
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * Properly update the value when the checkbox is (un)ticked to trigger
         * possible onchanges.
         *
         * @private
         */
        _onChange(ev) {
            this._setValue(ev.target.checked);
        }
        /**
         * Implement keyboard movements. Mostly useful for its environment, such
         * as a list view.
         *
         * @override
         * @private
         * @param {KeyEvent} ev
         */
        _onKeydown(ev) {
            switch (ev.which) {
                case $.ui.keyCode.ENTER:
                    // prevent subsequent 'click' event (see _onKeydown of AbstractField)
                    ev.preventDefault();
                    this._setValue(!this.value);
                    return;
                case $.ui.keyCode.UP:
                case $.ui.keyCode.RIGHT:
                case $.ui.keyCode.DOWN:
                case $.ui.keyCode.LEFT:
                    ev.preventDefault();
            }
            super._onKeydown(ev);
        }
    }
    FieldBoolean.components = { CustomCheckbox };
    FieldBoolean.description = _lt("Checkbox");
    FieldBoolean.supportedFieldTypes = ['boolean'];
    FieldBoolean.template = 'web.FieldBoolean';


    return {
        FieldBadge,
        FieldBoolean,
    };
});
