odoo.define('web.AbstractField', function (require) {
"use strict";

/**
 * This is the basic field widget used by all the views to render a field in a view.
 * These field widgets are mostly common to all views, in particular form and list
 * views.
 *
 * The responsabilities of a field widget are mainly:
 * - render a visual representation of the current value of a field
 * - that representation is either in 'readonly' or in 'edit' mode
 * - notify the rest of the system when the field has been changed by
 *   the user (in edit mode)
 *
 * Notes
 * - the widget is not supposed to be able to switch between modes.  If another
 *   mode is required, the view will take care of instantiating another widget.
 * - notify the system when its value has changed and its mode is changed to 'readonly'
 * - notify the system when some action has to be taken, such as opening a record
 * - the Field widget should not, ever, under any circumstance, be aware of
 *   its parent.  The way it communicates changes with the rest of the system is by
 *   triggering events (with trigger_up).  These events bubble up and are interpreted
 *   by the most appropriate parent.
 *
 * Also, in some cases, it may not be practical to have the same widget for all
 * views. In that situation, you can have a 'view specific widget'.  Just register
 * the widget in the registry prefixed by the view type and a dot.  So, for example,
 * a form specific many2one widget should be registered as 'form.many2one'.
 *
 * @module web.AbstractField
 */

var field_utils = require('web.field_utils');
var Widget = require('web.Widget');

var AbstractField = Widget.extend({
    events: {
        'keydown': '_onKeydown',
    },
    custom_events: {
        navigation_move: '_onNavigationMove',
    },

    /**
     * Determines if the field can be quick editable which means that when
     * the field is clicked and if it's quick editable, it will trigger an event
     * to the form view to switch into edit mode and then it'll perform
     * some action (@see quickEdit)
     */
    isQuickEditable: false,
    /**
     * List of selectors matching elements that must never trigger the 'quick_edit'
     * event when being clicked on.
     */
    quickEditExclusion: [],
    /**
    * An object representing fields to be fetched by the model eventhough not present in the view
    * This object contains "field name" as key and an object as value.
    * That value object must contain the key "type"
    * see FieldBinaryImage for an example.
    */
    fieldDependencies: {},

    /**
     * If this flag is set to true, the field widget will be reset on every
     * change which is made in the view (if the view supports it). This is
     * currently a form view feature.
     */
    resetOnAnyFieldChange: false,
    /**
     * If this flag is given a string, the related BasicModel will be used to
     * initialize specialData the field might need. This data will be available
     * through this.record.specialData[this.name].
     *
     * @see BasicModel._fetchSpecialData
     */
    specialData: false,
    /**
     * to override to indicate which field types are supported by the widget
     *
     * @type Array<String>
     */
    supportedFieldTypes: [],

    /**
     * To override to give a user friendly name to the widget.
     *
     * @type <string>
     */
    description: "",
    /**
     * Currently only used in list view.
     * If this flag is set to true, the list column name will be empty.
     */
    noLabel: false,
    /**
     * Currently only used in list view.
     * If set, this value will be displayed as column name.
     */
    label: '',
    /**
     * Abstract field class
     *
     * @constructor
     * @param {Widget} parent
     * @param {string} name The field name defined in the model
     * @param {Object} record A record object (result of the get method of
     *   a basic model)
     * @param {Object} [options]
     * @param {string} [options.mode=readonly] should be 'readonly' or 'edit'
     */
    init: function (parent, name, record, options) {
        this._super(parent);
        options = options || {};

        // 'name' is the field name displayed by this widget
        this.name = name;

        // the datapoint fetched from the model
        this.record = record;

        // the 'field' property is a description of all the various field properties,
        // such as the type, the comodel (relation), ...
        this.field = record.fields[name];

        // the 'viewType' is the type of the view in which the field widget is
        // instantiated. For standalone widgets, a 'default' viewType is set.
        this.viewType = options.viewType || 'default';

        // the 'attrs' property contains the attributes of the xml 'field' tag,
        // the inner views...
        var fieldsInfo = record.fieldsInfo[this.viewType];
        this.attrs = options.attrs || (fieldsInfo && fieldsInfo[name]) || {};

        // the 'additionalContext' property contains the attributes to pass through the context.
        this.additionalContext = options.additionalContext || {};

        // this property tracks the current (parsed if needed) value of the field.
        // Note that we don't use an event system anymore, using this.get('value')
        // is no longer valid.
        this.value = record.data[name];

        // recordData tracks the values for the other fields for the same record.
        // note that it is expected to be mostly a readonly property, you cannot
        // use this to try to change other fields value, this is not how it is
        // supposed to work. Also, do not use this.recordData[this.name] to get
        // the current value, this could be out of sync after a _setValue.
        this.recordData = record.data;

        // the 'string' property is a human readable (and translated) description
        // of the field. Mostly useful to be displayed in various places in the
        // UI, such as tooltips or create dialogs.
        this.string = this.attrs.string || this.field.string || this.name;

        // Widget can often be configured in the 'options' attribute in the
        // xml 'field' tag.  These options are saved (and evaled) in nodeOptions
        this.nodeOptions = this.attrs.options || {};

        // dataPointID is the id corresponding to the current record in the model.
        // Its intended use is to be able to tag any messages going upstream,
        // so the view knows which records was changed for example.
        this.dataPointID = record.id;

        // this is the res_id for the record in database.  Obviously, it is
        // readonly.  Also, when the user is creating a new record, there is
        // no res_id.  When the record will be created, the field widget will
        // be destroyed (when the form view switches to readonly mode) and a new
        // widget with a res_id in mode readonly will be created.
        this.res_id = record.res_id;

        // useful mostly to trigger rpcs on the correct model
        this.model = record.model;

        // a widget can be in two modes: 'edit' or 'readonly'.  This mode should
        // never be changed, if a view changes its mode, it will destroy and
        // recreate a new field widget.
        this.mode = options.mode || "readonly";

        // the widget can be readonly because of a modifier
        this.hasReadonlyModifier = options.hasReadonlyModifier || false;

        // this flag tracks if the widget is in a valid state, meaning that the
        // current value represented in the DOM is a value that can be parsed
        // and saved.  For example, a float field can only use a number and not
        // a string.
        this._isValid = true;

        // this is the last value that was set by the user, unparsed.  This is
        // used to avoid setting the value twice in a row with the exact value.
        this.lastSetValue = undefined;

        // formatType is used to determine which format (and parse) functions
        // to call to format the field's value to insert into the DOM (typically
        // put into a span or an input), and to parse the value from the input
        // to send it to the server. These functions are chosen according to
        // the 'widget' attrs if is is given, and if it is a valid key, with a
        // fallback on the field type, ensuring that the value is formatted and
        // displayed according to the chosen widget, if any.
        this.formatType = this.attrs.widget in field_utils.format ?
                            this.attrs.widget :
                            this.field.type;
        // formatOptions (resp. parseOptions) is a dict of options passed to
        // calls to the format (resp. parse) function.
        this.formatOptions = {};
        this.parseOptions = {};

        // if we add decorations, we need to reevaluate the field whenever any
        // value from the record is changed
        if (this.attrs.decorations) {
            this.resetOnAnyFieldChange = true;
        }
        this._canQuickEdit = this.isQuickEditable;
    },
    /**
     * When a field widget is appended to the DOM, its start method is called,
     * and will automatically call render. Most widgets should not override this.
     *
     * @returns {Promise}
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$el.attr('name', self.name);
            self.$el.addClass('o_field_widget');
            self.$el.toggleClass('o_quick_editable', self._canQuickEdit);
            if (self.viewType === 'form') {
                self.$el.on('click', self._onClick.bind(self));
            }
            return self._render();
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Activates the field widget. By default, activation means focusing and
     * selecting (if possible) the associated focusable element. The selecting
     * part can be disabled.  In that case, note that the focused input/textarea
     * will have the cursor at the very end.
     *
     * @param {Object} [options]
     * @param {boolean} [options.noselect=false] if false and the input
     *   is of type text or textarea, the content will also be selected
     * @param {Event} [options.event] the event which fired this activation
     * @returns {boolean} true if the widget was activated, false if the
     *                    focusable element was not found or invisible
     */
    activate: function (options) {
        if (this.isFocusable()) {
            var $focusable = this.getFocusableElement();
            $focusable.focus();
            if ($focusable.is('input[type="text"], textarea')) {
                $focusable[0].selectionStart = $focusable[0].selectionEnd = $focusable[0].value.length;
                if (options && !options.noselect) {
                    $focusable.select();
                }
            }
            return true;
        }
        return false;
    },
    /**
     * This function should be implemented by widgets that are not able to
     * notify their environment when their value changes (maybe because their
     * are not aware of the changes) or that may have a value in a temporary
     * state (maybe because some action should be performed to validate it
     * before notifying it). This is typically called before trying to save the
     * widget's value, so it should call _setValue() to notify the environment
     * if the value changed but was not notified.
     *
     * @abstract
     * @returns {Promise|undefined}
     */
    commitChanges: function () {},
    /**
     * This function is called when the form view auto focus a field for
     * quick editing. Some fields have a special behaviour for the quick edit
     * like the checkbox: when we click on checkbox to quick-edit it,
     * it toggles its value as we've already been in edit mode.
     *
     * @param {any} extraInfo info to change the behaviour
     */
    quickEdit: function (extraInfo) {
        if (this._canQuickEdit && this.mode !== "readonly") {
            this._quickEdit(extraInfo);
        }
    },
    /**
     * Returns the main field's DOM element (jQuery form) which can be focused
     * by the browser.
     *
     * @returns {jQuery} main focusable element inside the widget
     */
    getFocusableElement: function () {
        return $();
    },
    /**
     * Returns whether or not the field is empty and can thus be hidden. This
     * method is typically called when the widget is in readonly, to hide it
     * (and its label) if it is empty.
     *
     * @returns {boolean}
     */
    isEmpty: function () {
        return !this.isSet();
    },
    /**
     * Returns true iff the widget has a visible element that can take the focus
     *
     * @returns {boolean}
     */
    isFocusable: function () {
        var $focusable = this.getFocusableElement();
        return $focusable.length && $focusable.is(':visible');
    },
    /**
     * this method is used to determine if the field value is set to a meaningful
     * value.  This is useful to determine if a field should be displayed as empty
     *
     * @returns {boolean}
     */
    isSet: function () {
        return !!this.value;
    },
    /**
     * A field widget is valid if it was checked as valid the last time its
     * value was changed by the user. This is checked before saving a record, by
     * the view.
     *
     * Note: this is the responsibility of the view to check that required
     * fields have a set value.
     *
     * @returns {boolean} true/false if the widget is valid
     */
    isValid: function () {
        return this._isValid;
    },
    /**
     * this method is supposed to be called from the outside of field widgets.
     * The typical use case is when an onchange has changed the widget value.
     * It will reset the widget to the values that could have changed, then will
     * rerender the widget.
     *
     * @param {any} record
     * @param {OdooEvent} [event] an event that triggered the reset action. It
     *   is optional, and may be used by a widget to share information from the
     *   moment a field change event is triggered to the moment a reset
     *   operation is applied.
     * @returns {Promise} A promise, which resolves when the widget rendering
     *   is complete
     */
    reset: function (record, event) {
        this._reset(record, event);
        return this._render() || Promise.resolve();
    },
    /**
     * Remove the invalid class on a field
     */
    removeInvalidClass: function () {
        this.$el.removeClass('o_field_invalid');
        this.$el.removeAttr('aria-invalid');
    },
    /**
     * Sets the given id on the focusable element of the field and as 'for'
     * attribute of potential internal labels.
     *
     * @param {string} id
     */
    setIDForLabel: function (id) {
        this.getFocusableElement().attr('id', id);
    },
    /**
     * add the invalid class on a field
     */
    setInvalidClass: function () {
        this.$el.addClass('o_field_invalid');
        this.$el.attr('aria-invalid', 'true');
    },
    /**
     * Update the modifiers with the newest value.
     * Now this.attrs.modifiersValue can be used consistantly even with
     * conditional modifiers inside field widgets, and without needing new
     * events or synchronization between the widgets, renderer and controller
     *
     * @param {Object | null} modifiers  the updated modifiers
     * @override
     */
    updateModifiersValue: function(modifiers) {
        this.attrs.modifiersValue = modifiers || {};
    },


    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Apply field decorations (only if field-specific decorations have been
     * defined in an attribute).
     *
     * @private
     */
    _applyDecorations: function () {
        var self = this;
        this.attrs.decorations.forEach(function (dec) {
            var isToggled = py.PY_isTrue(
                py.evaluate(dec.expression, self.record.evalContext)
            );
            const className = self._getClassFromDecoration(dec.name);
            self.$el.toggleClass(className, isToggled);
        });
    },
    /**
     * @private
     * @see quickEdit
     * @param {any} extraInfo info to change the behaviour
     */
    _quickEdit: function (extraInfo) {
        this.activate({noAutomaticCreate: true});
    },
    /**
     * Converts the value from the field to a string representation.
     *
     * @private
     * @param {any} value (from the field type)
     * @param {string} [formatType=this.formatType] the formatter to use
     * @returns {string}
     */
    _formatValue: function (value, formatType) {
        formatType = formatType || this.formatType;
        if (!formatType) {
            throw new Error(`Missing format type for '${this.name}' value from the '${this.model}' model`);
        }
        var options = _.extend({}, this.nodeOptions, { data: this.recordData }, this.formatOptions);
        return field_utils.format[formatType](value, this.field, options);
    },
    /**
     * Returns the className corresponding to a given decoration. A
     * decoration is of the form 'decoration-%s'. By default, replaces
     * 'decoration' by 'text'.
     *
     * @private
     * @param {string} decoration must be of the form 'decoration-%s'
     * @returns {string}
     */
    _getClassFromDecoration: function (decoration) {
        return `text-${decoration.split('-')[1]}`;
    },
    /**
     * @private
     * @param {MouseEvent} ev
     * @returns {Object}
     */
    _getQuickEditExtraInfo(ev) {
        return {};
    },
    /**
     * Compares the given value with the last value that has been set.
     * Note that we compare unparsed values. Handles the special case where no
     * value has been set yet, and the given value is the empty string.
     *
     * @private
     * @param {any} value
     * @returns {boolean} true iff values are the same
     */
    _isLastSetValue: function (value) {
        return this.lastSetValue === value || (this.value === false && value === '');
    },
    /**
     * This method check if a value is the same as the current value of the
     * field.  For example, a fieldDate widget might want to use the moment
     * specific value isSame instead of ===.
     *
     * This method is used by the _setValue method.
     *
     * @private
     * @param {any} value
     * @returns {boolean}
     */
    _isSameValue: function (value) {
        return this.value === value;
    },
    /**
     * Converts a string representation to a valid value.
     *
     * @private
     * @param {string} value
     * @returns {any}
     */
    _parseValue: function (value) {
        return field_utils.parse[this.formatType](value, this.field, this.parseOptions);
    },
    /**
     * main rendering function.  Override this if your widget has the same render
     * for each mode.  Note that this function is supposed to be idempotent:
     * the result of calling 'render' twice is the same as calling it once.
     * Also, the user experience will be better if your rendering function is
     * synchronous.
     *
     * @private
     * @returns {Promise|undefined}
     */
    _render: function () {
        if (this.attrs.decorations) {
            this._applyDecorations();
        }
        if (this.mode === 'edit') {
            return this._renderEdit();
        } else if (this.mode === 'readonly') {
            return this._renderReadonly();
        }
    },
    /**
     * Render the widget in edit mode.  The actual implementation is left to the
     * concrete widget.
     *
     * @private
     * @returns {Promise|undefined}
     */
    _renderEdit: function () {
    },
    /**
     * Render the widget in readonly mode.  The actual implementation is left to
     * the concrete widget.
     *
     * @private
     * @returns {Promise|undefined}
     */
    _renderReadonly: function () {
    },
    /**
     * pure version of reset, can be overridden, called before render()
     *
     * @private
     * @param {any} record
     * @param {OdooEvent} event the event that triggered the change
     */
    _reset: function (record, event) {
        this.lastSetValue = undefined;
        this.record = record;
        this.value = record.data[this.name];
        this.recordData = record.data;
    },
    /**
     * this method is called by the widget, to change its value and to notify
     * the outside world of its new state.  This method also validates the new
     * value.  Note that this method does not rerender the widget, it should be
     * handled by the widget itself, if necessary.
     *
     * @private
     * @param {any} value
     * @param {Object} [options]
     * @param {boolean} [options.doNotSetDirty=false] if true, the basic model
     *   will not consider that this field is dirty, even though it was changed.
     *   Please do not use this flag unless you really need it.  Our only use
     *   case is currently the pad widget, which does a _setValue in the
     *   renderEdit method.
     * @param {boolean} [options.notifyChange=true] if false, the basic model
     *   will not notify and not trigger the onchange, even though it was changed.
     * @param {boolean} [options.forceChange=false] if true, the change event will be
     *   triggered even if the new value is the same as the old one
     * @returns {Promise}
     */
    _setValue: function (value, options) {
        // we try to avoid doing useless work, if the value given has not changed.
        if (this._isLastSetValue(value)) {
            return Promise.resolve();
        }
        this.lastSetValue = value;
        try {
            value = this._parseValue(value);
            this._isValid = true;
        } catch (e) {
            this._isValid = false;
            this.trigger_up('set_dirty', {dataPointID: this.dataPointID});
            return Promise.reject({message: "Value set is not valid"});
        }
        if (!(options && options.forceChange) && this._isSameValue(value)) {
            return Promise.resolve();
        }
        var self = this;
        return new Promise(function (resolve, reject) {
            var changes = {};
            changes[self.name] = value;
            self.trigger_up('field_changed', {
                dataPointID: self.dataPointID,
                changes: changes,
                viewType: self.viewType,
                doNotSetDirty: options && options.doNotSetDirty,
                notifyChange: !options || options.notifyChange !== false,
                allowWarning: options && options.allowWarning,
                onSuccess: resolve,
                onFailure: reject,
            });
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Triggers quick edit only if the field is authorized to do it.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClick: function (ev) {
        if (!this.hasReadonlyModifier && this._canQuickEdit && this.mode === 'readonly' &&
            !this.quickEditExclusion.some(x => ev.target.closest(x))
        ) {
            this.trigger_up('quick_edit', {
                fieldName: this.name,
                target: this.el,
                extraInfo: this._getQuickEditExtraInfo(ev),
            });
        }
    },
    /**
     * Intercepts navigation keyboard events to prevent their default behavior
     * and notifies the view so that it can handle it its own way.
     *
     * Note: the navigation keyboard events are stopped so that potential parent
     * abstract field does not trigger the navigation_move event a second time.
     * However, this might be controversial, we might wanna let the event
     * continue its propagation and flag it to say that navigation has already
     * been handled (TODO ?).
     *
     * @private
     * @param {KeyEvent} ev
     */
    _onKeydown: function (ev) {
        switch (ev.which) {
            case $.ui.keyCode.TAB:
                var event = this.trigger_up('navigation_move', {
                    direction: ev.shiftKey ? 'previous' : 'next',
                });
                if (event.is_stopped()) {
                    ev.preventDefault();
                    ev.stopPropagation();
                }
                break;
            case $.ui.keyCode.ENTER:
                // We preventDefault the ENTER key because of two coexisting behaviours:
                // - In HTML5, pressing ENTER on a <button> triggers two events: a 'keydown' AND a 'click'
                // - When creating and opening a dialog, the focus is automatically given to the primary button
                // The end result caused some issues where a modal opened by an ENTER keypress (e.g. saving
                // changes in multiple edition) confirmed the modal without any intentionnal user input.
                ev.preventDefault();
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'next_line'});
                break;
            case $.ui.keyCode.ESCAPE:
                this.trigger_up('navigation_move', {direction: 'cancel', originalEvent: ev});
                break;
            case $.ui.keyCode.UP:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'up'});
                break;
            case $.ui.keyCode.RIGHT:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'right'});
                break;
            case $.ui.keyCode.DOWN:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'down'});
                break;
            case $.ui.keyCode.LEFT:
                ev.stopPropagation();
                this.trigger_up('navigation_move', {direction: 'left'});
                break;
        }
    },
    /**
     * Updates the target data value with the current AbstractField instance.
     * This allows to consider the parent field in case of nested fields. The
     * field which triggered the event is still accessible through ev.target.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onNavigationMove: function (ev) {
        ev.data.target = this;
    },
});

return AbstractField;

});
