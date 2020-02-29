odoo.define('web.AbstractFieldOwl', function (require) {
    "use strict";

    const field_utils = require('web.field_utils');
    const { useListener } = require('web.custom_hooks');

    const { onMounted, onPatched } = owl.hooks;

    /**
     * This file defines the Owl version of the AbstractField. Specific fields
     * written in Owl should override this component.
     *
     * Note that the API is not complete yet. Some features may not work properly
     * yet (e.g. part of keyboard navigation, invalid fields notification).
     *
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
     * @module web.AbstractFieldOwl
     */
    class AbstractField extends owl.Component {
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
        constructor(parent, props) {
            super(parent, props);

            const options = Object.assign({}, props.options);
            const record = props.record;
            // 'name' is the field name displayed by this widget
            this.name = props.fieldName;

            // the datapoint fetched from the model
            this.record = record;

            // the 'field' property is a description of all the various field properties,
            // such as the type, the comodel (relation), ...
            this.field = record.fields[this.name];

            // the 'viewType' is the type of the view in which the field widget is
            // instantiated. For standalone widgets, a 'default' viewType is set.
            this.viewType = options.viewType || 'default';

            // the 'attrs' property contains the attributes of the xml 'field' tag,
            // the inner views...
            const fieldsInfo = record.fieldsInfo[this.viewType];
            this.attrs = options.attrs || (fieldsInfo && fieldsInfo[this.name]) || {};

            // the 'additionalContext' property contains the attributes to pass through the context.
            this.additionalContext = options.additionalContext || {};

            // this property tracks the current (parsed if needed) value of the field.
            // Note that we don't use an event system anymore, using this.get('value')
            // is no longer valid.
            this.value = record.data[this.name];

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

            useListener('keydown', this._onKeydown);
            useListener('navigation-move', this._onNavigationMove);
            onMounted(() => this._applyDecorations());
            onPatched(() => this._applyDecorations());
        }

        /**
         * Hack: studio tries to find the field with a selector base on its
         * name, before it is mounted into the DOM. Ideally, this should be
         * done in the onMounted hook, but in this case we are too late, and
         * Studio finds nothing. As a consequence, the field can't be edited
         * by clicking on its label (or on the row formed by the pair label-field).
         *
         * TODO: move this to mounted at some point?
         *
         * @override
         */
        __patch() {
            const res = super.__patch(...arguments);
            this.el.setAttribute('name', this.name);
            this.el.classList.add('o_field_widget');
            return res;
        }

        /**
         * @async
         * @param {Object} [nextProps]
         * @param {Object} [nextProps.record]
         * @param {Object} [nextProps.event]
         * @returns {Promise}
         */
        async willUpdateProps(nextProps) {
            this.record = nextProps.record;
            this.recordData = this.record.data;
            this.value = this.recordData[this.name];
            this.lastSetValue = undefined;
            return super.willUpdateProps(nextProps);
        }

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * Returns the main field's DOM element (jQuery form) which can be focused
         * by the browser.
         *
         * @returns {HTMLElement|null} main focusable element inside the widget
         */
        get focusableElement() {
            return null;
        }
        /**
         * Returns whether or not the field is empty and can thus be hidden. This
         * method is typically called when the widget is in readonly, to hide it
         * (and its label) if it is empty.
         *
         * @returns {boolean}
         */
        get isEmpty() {
            return !this.isSet;
        }
        /**
         * Returns true if the widget has a visible element that can take the focus
         *
         * @returns {boolean}
         */
        get isFocusable() {
            const focusable = this.focusableElement;
            // check if element is visible
            return focusable && !!(focusable.offsetWidth || focusable.offsetHeight
                || focusable.getClientRects().length);
        }
        /**
         * @returns {boolean}
         */
        get isSet() {
            return !!this.value;
        }
        /**
         * @returns {boolean}
         */
        get isValid() {
            return this._isValid;
        }
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
        commitChanges() {}
        /**
         * Sets the given id on the focusable element of the field and as 'for'
         * attribute of potential internal labels.
         *
         * @param {string} id
         */
        setIDForLabel(id) {
            if (this.focusableElement) {
                this.focusableElement.setAttribute('id', id);
            }
        }
        /**
         * Update the modifiers with the newest value.
         * Now this.attrs.modifiersValue can be used consistantly even with
         * conditional modifiers inside field widgets, and without needing new
         * events or synchronization between the widgets, renderer and controller
         *
         * @param {Object | null} modifiers  the updated modifiers
         * @override
         */
        updateModifiersValue(modifiers) {
            this.attrs.modifiersValue = modifiers || {};
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * Apply field decorations (only if field-specific decorations have been
         * defined in an attribute).
         *
         * @private
         */
        _applyDecorations() {
            for (const dec of this.attrs.decorations || []) {
                const isToggled = py.PY_isTrue(
                    py.evaluate(dec.expression, this.record.evalContext)
                );
                this.el.classList.toggle(dec.className, isToggled);
            }
        }
        /**
         * Converts the value from the field to a string representation.
         *
         * @private
         * @param {any} value (from the field type)
         * @returns {string}
         */
        _formatValue(value) {
            const options = _.extend({}, this.nodeOptions,
                { data: this.recordData }, this.formatOptions);
            return field_utils.format[this.formatType](value, this.field, options);
        }
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
         * This method is called by the widget, to change its value and to notify
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
        _setValue(value, options) {
            // we try to avoid doing useless work, if the value given has not
            // changed.  Note that we compare the unparsed values.
            if (this.lastSetValue === value || (this.value === false && value === '')) {
                return Promise.resolve();
            }
            this.lastSetValue = value;
            try {
                value = this._parseValue(value);
                this._isValid = true;
            } catch (e) {
                this._isValid = false;
                this.trigger('set-dirty', {dataPointID: this.dataPointID});
                return Promise.reject({message: "Value set is not valid"});
            }
            if (!(options && options.forceChange) && this._isSameValue(value)) {
                return Promise.resolve();
            }
            return new Promise((resolve, reject) => {
                const changes = {};
                changes[this.name] = value;
                this.trigger('field-changed', {
                    dataPointID: this.dataPointID,
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

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

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
        _onKeydown(ev) {
            switch (ev.which) {
                case $.ui.keyCode.TAB:
                    this.trigger('navigation-move', {
                        direction: ev.shiftKey ? 'previous' : 'next',
                    });
                    // TODO: stop/prevent original event if navigation-move event
                    // has been handled
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
     * An object representing fields to be fetched by the model eventhough not present in the view
     * This object contains "field name" as key and an object as value.
     * That value object must contain the key "type"
     * see FieldBinaryImage for an example.
     */
    AbstractField.fieldDependencies = {};
    /**
     * If this flag is set to true, the field widget will be reset on every
     * change which is made in the view (if the view supports it). This is
     * currently a form view feature.
     */
    AbstractField.resetOnAnyFieldChange = false;
    /**
     * If this flag is given a string, the related BasicModel will be used to
     * initialize specialData the field might need. This data will be available
     * through this.record.specialData[this.name].
     *
     * @see BasicModel._fetchSpecialData
     */
    AbstractField.specialData = false;
    /**
     * to override to indicate which field types are supported by the widget
     *
     * @type Array<String>
     */
    AbstractField.supportedFieldTypes = [];
    /**
     * To override to give a user friendly name to the widget.
     *
     * @type <string>
     */
    AbstractField.description = "";
    /**
     * Currently only used in list view.
     * If this flag is set to true, the list column name will be empty.
     */
    AbstractField.noLabel = false;

    return AbstractField;
});
