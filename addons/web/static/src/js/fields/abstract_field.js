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
var pyeval = require('web.pyeval');
var Widget = require('web.Widget');

var AbstractField = Widget.extend({
    className: 'o_field_widget',
    events: {
        'keydown': '_onKeydown',
    },
    /**
     * if this flag is set to true, the rest of the web client will assume that
     * it is not editable.  For example, the list view in editable mode will
     * skip the widget when pressing tab
     */
    readonly: false,

    /**
     * If this flag is set to true, the field widget will be reset on every
     * change which is made in the view (if the view supports it). This is
     * currently a form view feature.
     */
    resetOnAnyFieldChange: false,

    /**
     * if true, the widget will replace a cell in an editable list view
     */
    replace_element: false,
    /**
     * to override to indicate which field types are supported by the widget
     */
    supportedFieldTypes: [],

    /**
     * Abstract field class
     *
     * @constructor
     * @param {Widget} parent
     * @param {string} name The field name defined in the model
     * @param {Object} record A record object (result of the get method of a basic model)
     * @param {Object} [options]
     * @param {string} [options.mode=readonly] should be 'readonly' or 'edit'
     * @param {string} [options.required=false]
     * @param {string} [options.idForLabel]
     */
    init: function (parent, name, record, options) {
        this._super(parent);
        options = options || {};

        // 'name' is the field name displayed by this widget
        this.name = name;

        // the 'field' property is a description of all the various field properties,
        // such as the type, the comodel (relation), ...
        this.field = record.fields[name];

        // the 'attrs' property contains the attributes of the xml 'field' tag
        this.attrs = record.fieldAttrs[name] || {};

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
        this.nodeOptions = pyeval.py_eval(this.attrs.options || '{}', this.recordData);

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

        // this flag tracks if the widget is in a valid state, meaning that the
        // current value represented in the DOM is a value that can be parsed
        // and saved.  For example, a float field can only use a number and not
        // a string.
        this._isValid = true;

        // the 'required' flag is basically only needed to determine if the widget
        // is in a valid state (not valid if empty and required)
        this.required = options.required || false;

        // the 'idForLabel' is the (html) id that should be set to the relevent
        // dom entity.  If done correctly, clicking on the corresponding label
        // (in form view) will focus and select the value.
        this.idForLabel = options.idForLabel;
    },
    /**
     * When a field widget is appended to the DOM, its start method is called,
     * and will automatically call render. Most widgets should not override this.
     *
     * @returns {Deferred}
     */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self._render();
            if (self.required) {
                self.$el.addClass('o_form_required');
            }
            self.$el.attr('name', self.name);
        });
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Right now, this function is only used in editable list view when the user
     * select a cell.  The corresponding widget will be activated, which in general
     * means that the input text will be focused and selected
     */
    activate: function () {
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
     * a field widget is valid if its value is valid and if there is a value when
     * it is required.  This is checked before saving a record, by the form view.
     *
     * @returns {boolean}
     */
    isValid: function () {
        return this._isValid && !(this.required && !this.isSet());
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
     * @returns {Deferred} A Deferred, which resolves when the widget rendering
     *   is complete
     */
    reset: function (record, event) {
        this._reset(record, event);
        return this._render();
    },
    /**
     * @override performModelRPC from ServicesMixin
     * Adds the dataPointID to the option parameter so that the BasicController
     * (the FieldManagerMixin) knows the context to bind to the rpc call.
     */
    performModelRPC: function (model, method, args, kwargs, options) {
        return this._super(model, method, args, kwargs, _.extend({
            dataPointID: this.dataPointID,
            fieldName: this.name,
        }, options || {}));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * convert the value from the field to a string representation
     *
     * @private
     * @param {any} value (from the field type)
     * @returns {string}
     */
    _formatValue: function (value) {
        var options = _.extend({}, this.nodeOptions, { data: this.recordData });
        return field_utils.format[this.field.type](value, this.field, options);
    },
    /**
     * convert a string representation to a valid value, depending on the field
     * type.
     *
     * @private
     * @param {string} value
     * @returns {any}
     */
    _parseValue: function (value) {
        return field_utils.parse[this.field.type](value, this.field);
    },
    /**
     * main rendering function.  Override this if your widget has the same render
     * for each mode.  Note that this function is supposed to be idempotent:
     * the result of calling 'render' twice is the same as calling it once.
     * Also, the user experience will be better if your rendering function is
     * synchronous.
     *
     * @private
     * @returns {Deferred}
     */
    _render: function () {
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
     * @returns {Deferred}
     */
    _renderEdit: function () {
    },
    /**
     * Render the widget in readonly mode.  The actual implementation is left to
     * the concrete widget.
     *
     * @private
     * @returns {Deferred}
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
     */
    _setValue: function (value) {
        try {
            value = this._parseValue(value);
            this._isValid = true;
        } catch(e) {
            this._isValid = false;
        }
        var changes = {};
        changes[this.name] = value;
        this.trigger_up('field_changed', {
            dataPointID: this.dataPointID,
            changes: changes,
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * might be controversial: intercept the tab key, to allow the editable list
     * view to control where the focus is.
     *
     * @private
     * @param {KeyEvent} event
     */
    _onKeydown: function (event) {
        if (event.which === $.ui.keyCode.TAB) {
            this.trigger_up('move_next');
            event.preventDefault();
        }
    },
});

return AbstractField;

});
