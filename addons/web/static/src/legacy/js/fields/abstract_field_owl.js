odoo.define('web.AbstractFieldOwl', function (require) {
    "use strict";

    const field_utils = require('web.field_utils');
    const { useListener } = require("@web/core/utils/hooks");
    const { LegacyComponent } = require("@web/legacy/legacy_component");

    const { onWillUpdateProps, useEffect } = owl;

    /**
     * This file defines the Owl version of the AbstractField. Specific fields
     * written in Owl should override this component.
     *
     * =========================================================================
     *
     * /!\ This api works almost exactly like the legacy one but
     * /!\ it still could change! There are already a few methods that will be
     * /!\ removed like setIdForLabel, setInvalidClass, etc..
     *
     * =========================================================================
     *
     * This is the basic field component used by all the views to render a field in a view.
     * These field components are mostly common to all views, in particular form and list
     * views.
     *
     * The responsabilities of a field component are mainly:
     * - render a visual representation of the current value of a field
     * - that representation is either in 'readonly' or in 'edit' mode
     * - notify the rest of the system when the field has been changed by
     *   the user (in edit mode)
     *
     * Notes
     * - the component is not supposed to be able to switch between modes. If another
     *   mode is required, the view will take care of instantiating another component.
     * - notify the system when its value has changed and its mode is changed to 'readonly'
     * - notify the system when some action has to be taken, such as opening a record
     * - the Field component should not, ever, under any circumstance, be aware of
     *   its parent. The way it communicates changes with the rest of the system is by
     *   triggering events. These events bubble up and are interpreted
     *   by the most appropriate parent.
     *
     * Also, in some cases, it may not be practical to have the same component for all
     * views. In that situation, you can have a 'view specific component'. Just register
     * the component in the registry prefixed by the view type and a dot. So, for example,
     * a form specific many2one component should be registered as 'form.many2one'.
     *
     * @module web.AbstractFieldOwl
     */
    class AbstractField extends LegacyComponent {
        /**
         * Abstract field class
         *
         * @constructor
         * @param {Component} parent
         * @param {Object} props
         * @param {string} props.fieldName The field name defined in the model
         * @param {Object} props.record A record object (result of the get method
         *      of a basic model)
         * @param {Object} [props.options]
         * @param {string} [props.options.mode=readonly] should be 'readonly' or 'edit'
         * @param {string} [props.options.viewType=default]
         */
        setup() {
            this._canQuickEdit = this.constructor.isQuickEditable;
            this._isValid = true;
            // this is the last value that was set by the user, unparsed. This is
            // used to avoid setting the value twice in a row with the exact value.
            this._lastSetValue = undefined;

            useListener('click', this._onClick);
            useListener('keydown', this._onKeydown);
            useListener('navigation-move', this._onNavigationMove);
            useEffect(() => this._applyDecorations());
            useEffect(() => {
                this.el.setAttribute('name', this.name);
                this.el.classList.add('o_field_widget');
                this.el.classList.toggle('o_quick_editable', this._canQuickEdit);
            });
            onWillUpdateProps(() => {
                this._lastSetValue = undefined;
            });
        }

        //----------------------------------------------------------------------
        // Getters
        //----------------------------------------------------------------------

        /**
         * This contains the attributes to pass through the context.
         *
         * @returns {Object}
         */
        get additionalContext() {
            return this.options.additionalContext || {};
        }
        /**
         * This contains the attributes of the xml 'field' tag, the inner views...
         *
         * @returns {Object}
         */
        get attrs() {
            const fieldsInfo = this.record.fieldsInfo[this.viewType];
            return this.options.attrs || (fieldsInfo && fieldsInfo[this.name]) || {};
        }
        /**
         * Id corresponding to the current record in the model.
         * Its intended use is to be able to tag any messages going upstream,
         * so the view knows which records was changed for example.
         *
         * @returns {string}
         */
        get dataPointId() {
            return this.record.id;
        }
        /**
         * This is a description of all the various field properties,
         * such as the type, the comodel (relation), ...
         *
         * @returns {string}
         */
        get field() {
            return this.record.fields[this.name];
        }
        /**
         * Returns the main field's DOM element which can be focused by the browser.
         *
         * @returns {HTMLElement|null} main focusable element inside the component
         */
        get focusableElement() {
            return null;
        }
        /**
         * Returns the additional options pass to the format function.
         * Override this getter to add options.
         *
         * @returns {Object}
         */
        get formatOptions() {
            return {};
        }
        /**
         * Used to determine which format (and parse) functions
         * to call to format the field's value to insert into the DOM (typically
         * put into a span or an input), and to parse the value from the input
         * to send it to the server. These functions are chosen according to
         * the 'widget' attrs if is is given, and if it is a valid key, with a
         * fallback on the field type, ensuring that the value is formatted and
         * displayed according to the chosen widget, if any.
         *
         * @returns {string}
         */
        get formatType() {
            return this.attrs.widget in field_utils.format ?
                this.attrs.widget : this.field.type;
        }
        /**
         * Returns true if the component is readonly from a modifier
         *
         * @returns {boolean}
         */
        get hasReadonlyModifier() {
            return this.options.hasReadonlyModifier || false;
        }
        /**
         * Returns whether or not the field is empty and can thus be hidden. This
         * method is typically called when the component is in readonly, to hide it
         * (and its label) if it is empty.
         *
         * @returns {boolean}
         */
        get isEmpty() {
            return !this.isSet;
        }
        /**
         * Returns true if the component has a visible element that can take the focus
         *
         * @returns {boolean}
         */
        get isFocusable() {
            const focusable = this.focusableElement;
            // check if element is visible
            return focusable && !!(focusable.offsetWidth ||
                focusable.offsetHeight || focusable.getClientRects().length);
        }
        /**
         * Determines if the field value is set to a meaningful
         * value. This is useful to determine if a field should be displayed as empty
         *
         * @returns {boolean}
         */
        get isSet() {
            return !!this.value;
        }
        /**
         * Tracks if the component is in a valid state, meaning that the current
         * value represented in the DOM is a value that can be parsed and saved.
         * For example, a float field can only use a number and not a string.
         *
         * @returns {boolean}
         */
        get isValid() {
            return this._isValid;
        }
        /**
         * Fields can be in two modes: 'edit' or 'readonly'.
         *
         * @returns {string}
         */
        get mode() {
            return this.options.mode || "readonly";
        }
        /**
         * Useful mostly to trigger rpcs on the correct model.
         *
         * @returns {string}
         */
        get model() {
            return this.record.model;
        }
        /**
         * The field name displayed by this component.
         *
         * @returns {string}
         */
        get name() {
            return this.props.fieldName;
        }
        /**
         * Component can often be configured in the 'options' attribute in the
         * xml 'field' tag. These options are saved (and evaled) in nodeOptions.
         *
         * @returns {Object}
         */
        get nodeOptions() {
            return this.attrs.options || {};
        }
        /**
         * @returns {Object}
         */
        get options() {
            return this.props.options || {};
        }
        /**
         * Returns the additional options passed to the parse function.
         * Override this getter to add options.
         *
         * @returns {Object}
         */
        get parseOptions() {
            return {};
        }
        /**
         * The datapoint fetched from the model.
         *
         * @returns {Object}
         */
        get record() {
            return this.props.record;
        }
        /**
         * Tracks the values for the other fields for the same record.
         * note that it is expected to be mostly a readonly property, you cannot
         * use this to try to change other fields value, this is not how it is
         * supposed to work. Also, do not use this.recordData[this.name] to get
         * the current value, this could be out of sync after a _setValue.
         *
         * @returns {Object}
         */
        get recordData() {
            return this.record.data;
        }
        /**
         * If this flag is set to true, the field component will be reset on
         * every change which is made in the view (if the view supports it).
         * This is currently a form view feature.
         *
         * /!\ This getter could be removed when basic views (form, list, kanban)
         * are converted.
         *
         * @returns {boolean}
         */
        get resetOnAnyFieldChange() {
            return !!this.attrs.decorations;
        }
        /**
         * The res_id of the record in database.
         * When the user is creating a new record, there is no res_id.
         * When the record will be created, the field component will
         * be destroyed (when the form view switches to readonly mode) and a
         * new component with a res_id in mode readonly will be created.
         *
         * @returns {Number}
         */
        get resId() {
            return this.record.res_id;
        }
        /**
         * Human readable (and translated) description of the field.
         * Mostly useful to be displayed in various places in the
         * UI, such as tooltips or create dialogs.
         *
         * @returns {string}
         */
        get string() {
            return this.attrs.string || this.field.string || this.name;
        }
        /**
         * Tracks the current (parsed if needed) value of the field.
         *
         * @returns {any}
         */
        get value() {
            return this.record.data[this.name];
        }
        /**
         * The type of the view in which the field component is instantiated.
         * For standalone components, a 'default' viewType is set.
         *
         * @returns {string}
         */
        get viewType() {
            return this.options.viewType || 'default';
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Activates the field component. By default, activation means focusing and
         * selecting (if possible) the associated focusable element. The selecting
         * part can be disabled. In that case, note that the focused input/textarea
         * will have the cursor at the very end.
         *
         * @param {Object} [options]
         * @param {boolean} [options.noselect=false] if false and the input
         *   is of type text or textarea, the content will also be selected
         * @param {Event} [options.event] the event which fired this activation
         * @returns {boolean} true if the component was activated, false if the
         *                    focusable element was not found or invisible
         */
        activate(options) {
            if (this.isFocusable) {
                const focusable = this.focusableElement;
                focusable.focus();
                if (focusable.matches('input[type="text"], textarea')) {
                    focusable.selectionStart = focusable.selectionEnd = focusable.value.length;
                    if (options && !options.noselect) {
                        focusable.select();
                    }
                }
                return true;
            }
            return false;
        }
        /**
         * This function should be implemented by components that are not able to
         * notify their environment when their value changes (maybe because their
         * are not aware of the changes) or that may have a value in a temporary
         * state (maybe because some action should be performed to validate it
         * before notifying it). This is typically called before trying to save the
         * component's value, so it should call _setValue() to notify the environment
         * if the value changed but was not notified.
         *
         * @abstract
         * @returns {Promise|undefined}
         */
        commitChanges() {}
        /**
         * This function is called when the form view auto focus a field for
         * quick editing. Some fields have a special behaviour for the quick edit
         * like the checkbox: when we click on checkbox to quick-edit it,
         * it toggles its value as we've already been in edit mode.
         *
         * @param {any} extraInfo info to change the behaviour
         */
        quickEdit(extraInfo) {
            if (this._canQuickEdit && this.mode !== 'readonly') {
                this._quickEdit(extraInfo);
            }
        }
        /**
         * Remove the invalid class on a field
         *
         * This function should be removed when BasicRenderer will be rewritten in owl
         */
        removeInvalidClass() {
            this.el.classList.remove('o_field_invalid');
            this.el.removeAttribute('aria-invalid');
        }
        /**
         * Sets the given id on the focusable element of the field and as 'for'
         * attribute of potential internal labels.
         *
         * This function should be removed when BasicRenderer will be rewritten in owl
         *
         * @param {string} id
         */
        setIdForLabel(id) {
            if (this.focusableElement) {
                this.focusableElement.setAttribute('id', id);
            }
        }
        /**
         * add the invalid class on a field
         *
         * This function should be removed when BasicRenderer will be rewritten in owl
         */
        setInvalidClass() {
            this.el.classList.add('o_field_invalid');
            this.el.setAttribute('aria-invalid', 'true');
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Apply field decorations (only if field-specific decorations have been
         * defined in an attribute).
         *
         * This function should be removed when BasicRenderer will be rewritten in owl
         *
         * @private
         */
        _applyDecorations() {
            for (const dec of this.attrs.decorations || []) {
                const isToggled = py.PY_isTrue(
                    py.evaluate(dec.expression, this.record.evalContext)
                );
                const className = this._getClassFromDecoration(dec.name);
                this.el.classList.toggle(className, isToggled);
            }
        }
        /**
         * @private
         * @see quickEdit
         * @param {any} extraInfo info to change the behaviour
         */
        _quickEdit(extraInfo) {
            this.activate({noAutomaticCreate: true});
        }
        /**
         * Converts the value from the field to a string representation.
         *
         * @private
         * @param {any} value (from the field type)
         * @returns {string}
         */
        _formatValue(value) {
            const options = Object.assign({}, this.nodeOptions,
                { data: this.recordData }, this.formatOptions);
            return field_utils.format[this.formatType](value, this.field, options);
        }
        /**
         * Returns the className corresponding to a given decoration. A
         * decoration is of the form 'decoration-%s'. By default, replaces
         * 'decoration' by 'text'.
         *
         * @private
         * @param {string} decoration must be of the form 'decoration-%s'
         * @returns {string}
         */
        _getClassFromDecoration(decoration) {
            return `text-${decoration.split('-')[1]}`;
        }
        /**
         * @private
         * @param {MouseEvent} ev
         * @returns {Object}
         */
        _getQuickEditExtraInfo(ev) {
            return {};
        }
        /**
         * Compares the given value with the last value that has been set.
         * Note that we compare unparsed values. Handles the special case where no
         * value has been set yet, and the given value is the empty string.
         *
         * @private
         * @param {any} value
         * @returns {boolean} true iff values are the same
         */
        _isLastSetValue(value) {
            return this._lastSetValue === value || (this.value === false && value === '');
        }
        /**
         * This method check if a value is the same as the current value of the
         * field. For example, a fieldDate component might want to use the moment
         * specific value isSame instead of ===.
         *
         * This method is used by the _setValue method.
         *
         * @private
         * @param {any} value
         * @returns {boolean}
         */
        _isSameValue(value) {
            return this.value === value;
        }
        /**
         * Converts a string representation to a valid value.
         *
         * @private
         * @param {string} value
         * @returns {any}
         */
        _parseValue(value) {
            return field_utils.parse[this.formatType](value, this.field, this.parseOptions);
        }
        /**
         * This method is called by the component, to change its value and to notify
         * the outside world of its new state. This method also validates the new
         * value. Note that this method does not rerender the component, it should be
         * handled by the component itself, if necessary.
         *
         * @private
         * @param {any} value
         * @param {Object} [options]
         * @param {boolean} [options.doNotSetDirty=false] if true, the basic model
         *   will not consider that this field is dirty, even though it was changed.
         *   Please do not use this flag unless you really need it. Our only use
         *   case is currently the pad component, which does a _setValue in the
         *   renderEdit method.
         * @param {boolean} [options.notifyChange=true] if false, the basic model
         *   will not notify and not trigger the onchange, even though it was changed.
         * @param {boolean} [options.forceChange=false] if true, the change event will be
         *   triggered even if the new value is the same as the old one
         * @returns {Promise}
         */
        _setValue(value, options) {
            // we try to avoid doing useless work, if the value given has not changed.
            if (this._isLastSetValue(value)) {
                return Promise.resolve();
            }
            this._lastSetValue = value;
            try {
                value = this._parseValue(value);
                this._isValid = true;
            } catch (_e) {
                this._isValid = false;
                this.trigger('set-dirty', {dataPointID: this.dataPointId});
                return Promise.reject({message: "Value set is not valid"});
            }
            if (!(options && options.forceChange) && this._isSameValue(value)) {
                return Promise.resolve();
            }
            return new Promise((resolve, reject) => {
                const changes = {};
                changes[this.name] = value;
                this.trigger('field-changed', {
                    dataPointID: this.dataPointId,
                    changes: changes,
                    viewType: this.viewType,
                    doNotSetDirty: options && options.doNotSetDirty,
                    notifyChange: !options || options.notifyChange !== false,
                    allowWarning: options && options.allowWarning,
                    onSuccess: resolve,
                    onFailure: reject,
                });
            });
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * Triggers quick edit only if the field is authorized to do it.
         *
         * @private
         * @param {MouseEvent} ev
         */
        _onClick(ev) {
            if (this._canQuickEdit &&
                !this.constructor.quickEditExclusion.some(x => ev.target.closest(x))
            ) {
                this.trigger('quick-edit', {
                    fieldName: this.name,
                    target: this.el,
                    extraInfo: this._getQuickEditExtraInfo(ev),
                });
            }
        }
        /**
         * Intercepts navigation keyboard events to prevent their default behavior
         * and notifies the view so that it can handle it its own way.
         *
         * @private
         * @param {KeyEvent} ev
         */
        _onKeydown(ev) {
            switch (ev.which) {
                case $.ui.keyCode.TAB:
                    this.trigger('navigation-move', {
                        direction: ev.shiftKey ? 'previous' : 'next',
                        originalEvent: ev,
                    });
                    break;
                case $.ui.keyCode.ENTER:
                    // We preventDefault the ENTER key because of two coexisting behaviours:
                    // - In HTML5, pressing ENTER on a <button> triggers two events: a 'keydown' AND a 'click'
                    // - When creating and opening a dialog, the focus is automatically given to the primary button
                    // The end result caused some issues where a modal opened by an ENTER keypress (e.g. saving
                    // changes in multiple edition) confirmed the modal without any intentionnal user input.
                    ev.preventDefault();
                    ev.stopPropagation();
                    this.trigger('navigation-move', {direction: 'next_line'});
                    break;
                case $.ui.keyCode.ESCAPE:
                    this.trigger('navigation-move', {direction: 'cancel', originalEvent: ev});
                    break;
                case $.ui.keyCode.UP:
                    ev.stopPropagation();
                    this.trigger('navigation-move', {direction: 'up'});
                    break;
                case $.ui.keyCode.RIGHT:
                    ev.stopPropagation();
                    this.trigger('navigation-move', {direction: 'right'});
                    break;
                case $.ui.keyCode.DOWN:
                    ev.stopPropagation();
                    this.trigger('navigation-move', {direction: 'down'});
                    break;
                case $.ui.keyCode.LEFT:
                    ev.stopPropagation();
                    this.trigger('navigation-move', {direction: 'left'});
                    break;
            }
        }
        /**
         * Updates the target data value with the current AbstractField instance.
         * This allows to consider the parent field in case of nested fields. The
         * field which triggered the event is still accessible through ev.target.
         *
         * @private
         * @param {CustomEvent} ev
         */
        _onNavigationMove(ev) {
            ev.detail.target = this;
        }
    }

    /**
     * An object representing fields to be fetched by the model even though not
     * present in the view.
     * This object contains "field name" as key and an object as value.
     * That value object must contain the key "type"
     * @see FieldBinaryImage for an example.
     */
    AbstractField.fieldDependencies = {};
    /**
     * If this flag is given a string, the related BasicModel will be used to
     * initialize specialData the field might need. This data will be available
     * through this.record.specialData[this.name].
     *
     * @see BasicModel._fetchSpecialData
     */
    AbstractField.specialData = false;
    /**
     * to override to indicate which field types are supported by the component
     *
     * @type Array<string>
     */
    AbstractField.supportedFieldTypes = [];
    /**
     * To override to give a user friendly name to the component.
     *
     * @type string
     */
    AbstractField.description = "";
    /**
     * Currently only used in list view.
     * If this flag is set to true, the list column name will be empty.
     */
    AbstractField.noLabel = false;
    /**
     * Currently only used in list view.
     * If set, this value will be displayed as column name.
     */
    AbstractField.label = "";
    /**
     * Determines if the field can be quick editable which means that when
     * the field is clicked and if it's quick editable, it will trigger an event
     * to the form view to switch into edit mode and then it'll perform
     * some action (@see quickEdit)
     */
    AbstractField.isQuickEditable = false;
    /**
     * List of selectors matching elements that must never trigger the 'quick_edit'
     * event when being clicked on.
     */
    AbstractField.quickEditExclusion = [];

    return AbstractField;
});
