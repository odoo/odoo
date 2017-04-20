odoo.define('web.BasicRenderer', function (require) {
"use strict";

/**
 * The BasicRenderer is an abstract class designed to share code between all
 * views that uses a BasicModel. The main goal is to keep track of all field
 * widgets, and properly destroy them whenever a rerender is done. The widgets
 * and modifiers updates mechanism is also shared in the BasicRenderer.
 */
var AbstractRenderer = require('web.AbstractRenderer');
var config = require('web.config');
var core = require('web.core');
var Domain = require('web.Domain');

var qweb = core.qweb;

var BasicRenderer = AbstractRenderer.extend({
    custom_events: {
        /**
         * All basic renderers should be able to handle widget navigation
         * through the TAB key.
         */
        move_next: '_onMoveNext',
        move_previous: '_onMovePrevious',
    },
    /**
     * Basic renderers implements the concept of "mode", they can either be in
     * readonly mode or editable mode.
     *
     * @override
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this.activeActions = params.activeActions;
        this.viewType = params.viewType;
        this.mode = params.mode || 'readonly';
    },
    /**
     * Updates the internal state of the renderer to the new state. By default,
     * this also implements the recomputation of the modifiers and their
     * application to the DOM and the reset of the field widgets if needed.
     *
     * In case the given record is not found anymore, a whole re-rendering is
     * completed (possible if a change in a record caused an onchange which
     * erased the current record).
     *
     * We could always rerender the view from scratch, but then it would not be
     * as efficient, and we might lose some local state, such as the input focus
     * cursor, or the scrolling position.
     *
     * @param {Object} state
     * @param {string} id
     * @param {string[]} fields
     * @param {OdooEvent} ev
     * @returns {Deferred<AbstractField[]>} resolved with the list of widgets
     *                                      that have been reset
     */
    confirmChange: function (state, id, fields, ev) {
        this.state = state;

        var record = state.id === id ? state : _.findWhere(state.data, {id: id});
        if (!record) {
            return this._render();
        }

        var defs = [];

        // Reset all the field widgets that are marked as changed and the ones
        // which are configured to always be reset on any change
        var resetWidgets = [];
        _.each(this.allFieldWidgets[id], function (widget) {
            if (_.contains(fields, widget.name) || widget.resetOnAnyFieldChange) {
                defs.push(widget.reset(record, ev));
                resetWidgets.push(widget);
            }
        });

        // The modifiers update is done after widget resets as modifiers
        // associated callbacks need to have all the widgets with the proper
        // state before evaluation
        defs.push(this._updateAllModifiers(record));

        return $.when.apply($, defs).then(function () {
            return resetWidgets;
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Add a tooltip on a $node, depending on a field description
     *
     * @param {FieldWidget} widget
     * @param {$node} $node
     */
    _addFieldTooltip: function (widget, $node) {
        // optional argument $node, the jQuery element on which the tooltip
        // should be attached if not given, the tooltip is attached on the
        // widget's $el
        $node = $node.length ? $node : widget.$el;
        $node.tooltip({
            delay: { show: 1000, hide: 0 },
            title: function () {
                return qweb.render('WidgetLabel.tooltip', {
                    debug: config.debug,
                    widget: widget,
                });
            }
        });
    },
    /**
     * Activates the widget at the given index for the given record if possible
     * or the "next" possible one.
     *
     * @private
     * @param {Object} record
     * @param {integer} currentIndex
     * @param {integer} [inc=1] - the increment to use when searching for the
     *                          "next" possible one
     * @returns {integer} the index of the widget that was activated or -1 if
     *                    none was possible to activate
     */
    _activateFieldWidget: function (record, currentIndex, inc) {
        inc = inc === undefined ? 1 : inc;

        var activated;
        var recordWidgets = this.allFieldWidgets[record.id] || [];
        for (var i = 0 ; i < recordWidgets.length ; i++) {
            activated = recordWidgets[currentIndex].activate();
            if (activated) {
                return currentIndex;
            }

            currentIndex += inc;
            if (currentIndex >= recordWidgets.length) {
                currentIndex -= recordWidgets.length;
            } else if (currentIndex < 0) {
                currentIndex += recordWidgets.length;
            }
        }
        return -1;
    },
    /**
     * This is a wrapper of the {@see _activateFieldWidget} function to select
     * the next possible widget instead of the given one.
     *
     * @private
     * @param {Object} record
     * @param {integer} currentIndex
     * @return {integer}
     */
    _activateNextFieldWidget: function (record, currentIndex) {
        currentIndex = (currentIndex + 1) % (this.allFieldWidgets[record.id] || []).length;
        return this._activateFieldWidget(record, currentIndex, +1);
    },
    /**
     * This is a wrapper of the {@see _activateFieldWidget} function to select
     * the previous possible widget instead of the given one.
     *
     * @private
     * @param {Object} record
     * @param {integer} currentIndex
     * @return {integer}
     */
    _activatePreviousFieldWidget: function (record, currentIndex) {
        currentIndex = currentIndex ? (currentIndex - 1) : ((this.allFieldWidgets[record.id] || []).length - 1);
        return this._activateFieldWidget(record, currentIndex, -1);
    },
    /**
     * Does the necessary DOM updates to match the given modifiers data. The
     * modifiers data is supposed to contain the properly evaluated modifiers
     * associated to the given records and elements.
     *
     * @param {Object} modifiersData
     * @param {Object} record
     * @param {Object} [element] - do the update only on this element if given
     */
    _applyModifiers: function (modifiersData, record, element) {
        var self = this;
        var modifiers = modifiersData.evaluatedModifiers[record.id] || {};

        if (element) {
            _apply(element);
        } else {
            // Clone is necessary as the list might change during _.each
            _.each(_.clone(modifiersData.elementsByRecord[record.id]), _apply);
        }

        function _apply(element) {
            // If the view is in edit mode and that a widget have to switch
            // its "readonly" state, we have to re-render it completely
            if ('readonly' in modifiers
                && self.mode === "edit"
                && element.widget
                && (element.widget.mode === 'readonly') !== modifiers.readonly)
            {
                self._rerenderFieldWidget(element.widget, record);
                return; // Rerendering already applied the modifiers, no need to go further
            }

            // Toggle modifiers CSS classes if necessary
            element.$el.toggleClass("o_form_invisible", !!modifiers.invisible);
            element.$el.toggleClass("o_readonly", !!modifiers.readonly);
            element.$el.toggleClass("o_form_required", !!modifiers.required);

            // Call associated callback
            if (element.callback) {
                element.callback(element, modifiers, record);
            }
        }
    },
    /**
     * Determines if a given field widget value can be saved. For this to be
     * true, the widget must be valid (properly parsed value) and have a value
     * if the associated view field is required.
     *
     * @private
     * @param {AbstractField} widget
     * @returns {boolean|Deferred<boolean>} @see AbstractField.isValid
     */
    _canWidgetBeSaved: function (widget) {
        var modifiers = this._getEvaluatedModifiers(widget.__node, widget.record);
        var isSetOrNotRequired = (widget.isSet() || !modifiers.required);
        var isValid = widget.isValid();
        if (isValid instanceof $.Deferred) {
            return isValid.then(function (isValid) {
                return isValid && isSetOrNotRequired;
            });
        }
        return isValid && isSetOrNotRequired;
    },
    /**
     * Updates the modifiers evaluation associated to a given modifiers data and
     * a given record. This only updates the modifiers values. To see associated
     * DOM updates: @see _updateAllModifiers @see _applyModifiers.
     *
     * @private
     * @param {Object} modifiersData
     * @param {Object} record
     */
    _computeModifiers: function (modifiersData, record) {
        var evalContext = record.getEvalContext();
        modifiersData.evaluatedModifiers[record.id]
            = _.mapObject(modifiersData.modifiers, function (modifier) {
                return new Domain(modifier, evalContext).compute(evalContext);
            });
    },
    /**
     * Destroys a given widget associated to the given record and removes it
     * from internal referencing.
     *
     * @private
     * @param {Object} record
     * @param {AbstractField} widget
     * @returns {integer} the index of the removed widget
     */
    _destroyFieldWidget: function (record, widget) {
        var recordWidgets = this.allFieldWidgets[record.id];
        var index = recordWidgets.indexOf(widget);
        if (index >= 0) {
            recordWidgets.splice(index, 1);
        }
        this._unregisterModifiersElement(widget.__node, record, widget);
        widget.$el.destroy();
        return index;
    },
    /**
     * Searches for the last evaluation of the modifiers associated to the given
     * data (modifiers evaluation are supposed to always be up-to-date as soon
     * as possible).
     *
     * @private
     * @param {Object} node
     * @param {Object} record
     * @returns {Object} the evaluated modifiers associated to the given node
     *                   and record (not recomputed by the call)
     */
    _getEvaluatedModifiers: function (node, record) {
        var element = this._getModifiersData(node);
        if (!element) {
            return {};
        }
        return element.evaluatedModifiers[record.id] || {};
    },
    /**
     * Searches through the registered modifiers data for the one which is
     * related to the given node.
     *
     * @private
     * @param {Object} node
     * @returns {Object|undefined} related modifiers data if any
     *                             undefined otherwise
     */
    _getModifiersData: function (node) {
        return _.findWhere(this.allModifiersData, {node: node});
    },
    /**
     * Registers or updates the modifiers data associated to the given node.
     * This method is quiet complex as it handles all the needs of the basic
     * renderers:
     *
     * - On first registration, the modifiers are evaluated thanks to the given
     *   record. This allows nodes that will produce an AbstractField instance
     *   to have their modifiers registered before this field creation as we
     *   need the readonly modifier to be able to instantiate the AbstractField.
     *   (@see _computeModifiers).
     *
     * - On additional registrations, if the node was already registered but the
     *   record is different, we evaluate the modifiers for this record and
     *   saves them in the same object (without reparsing the modifiers).
     *
     * - On additional registrations, the modifiers are not reparsed (or
     *   reevaluated for an already seen record) but the given widget or DOM
     *   element is associated to the node modifiers.
     *
     * - The new elements are immediately adapted to match the modifiers and the
     *   given associated callback is called even if there is no modifiers on
     *   the node (@see _applyModifiers). This is indeed necessary as the
     *   callback is a description of what to do when a modifier changes. Even
     *   if there is no modifiers, this action must be performed on first
     *   rendering to avoid code duplication. If there is no modifiers, they
     *   will however not be registered for modifiers updates.
     *
     * - When a new element is given, it does not replace the old one, it is
     *   added as an additional element. This is indeed useful for nodes that
     *   will produce multiple DOM (as a list cell and its internal widget or
     *   a form field and its associated label).
     *   (@see _unregisterModifiersElement for removing an associated element.)
     *
     * Note: also on view rerendering, all the modifiers are forgotten so that
     * the renderer only keeps the ones associated to the current DOM state.
     *
     * @private
     * @param {Object} node
     * @param {Object} record
     * @param {jQuery|AbstractField} [element]
     * @param {Object} [options]
     * @param {Object} [options.callback] - the callback to call on registration
     *                                    and on modifiers updates
     * @returns {Object} for code efficiency, returns the last evaluated
     *                   modifiers for the given node and record.
     */
    _registerModifiers: function (node, record, element, options) {
        // Check if we already registered the modifiers for the given node
        // If yes, this is simply an update of the related element
        // If not, check the modifiers to see if it needs registration
        var modifiersData = this._getModifiersData(node);
        if (!modifiersData) {
            var modifiers = JSON.parse(node.attrs.modifiers || "{}"); // FIXME parsed multiple times (record switching, no modifiers, ...)
            modifiersData = {
                node: node,
                modifiers: modifiers,
                evaluatedModifiers: {},
                elementsByRecord: {},
            };
            if (!_.isEmpty(modifiers)) { // Register only if modifiers might change (TODO condition might be improved here)
                this.allModifiersData.push(modifiersData);
            }
        }

        // Evaluate if necessary
        if (!modifiersData.evaluatedModifiers[record.id]) {
            this._computeModifiers(modifiersData, record);
        }

        // Element might not be given yet (a second call to the function can
        // update the registration with the element)
        if (element) {
            var newElement = {};
            if (element instanceof jQuery) {
                newElement.$el = element;
            } else {
                newElement.widget = element;
                newElement.$el = element.$el;
            }
            if (options && options.callback) {
                newElement.callback = options.callback;
            }

            if (!modifiersData.elementsByRecord[record.id]) {
                modifiersData.elementsByRecord[record.id] = [];
            }
            modifiersData.elementsByRecord[record.id].push(newElement);

            this._applyModifiers(modifiersData, record, newElement);
        }

        return modifiersData.evaluatedModifiers[record.id];
    },
    /**
     * Render the view
     *
     * @override
     * @returns {Deferred}
     */
    _render: function () {
        var oldAllFieldWidgets = this.allFieldWidgets;
        this.allFieldWidgets = {}; // TODO maybe merging allFieldWidgets and allModifiersData into "nodesData" in some way could be great
        this.allModifiersData = [];
        return this._renderView().then(function () {
            _.each(oldAllFieldWidgets, function (recordWidgets) {
                _.each(recordWidgets, function (widget) {
                    widget.destroy();
                });
            });
        });
    },
    /**
     * Instantiates the appropriate AbstractField specialization for the given
     * node and prepares its rendering and addition to the DOM. Indeed, the
     * rendering of the widget will be started and the associated deferred will
     * be added to the 'defs' attribute. This is supposed to be created and
     * deleted by the calling code if necessary.
     * Note: for this implementation to work, AbstractField willStart methods
     * *must* be synchronous.
     *
     * @private
     * @param {Object} node
     * @param {Object} record
     * @param {Object} [options]
     * @param {Object} [modifiersOptions]
     * @returns {AbstractField}
     */
    _renderFieldWidget: function (node, record, options, modifiersOptions) {
        var fieldName = node.attrs.name;

        // Register the node-associated modifiers
        var modifiers = this._registerModifiers(node, record);

        // Initialize and register the widget
        // Readonly status is known as the modifiers have just been registered
        var Widget = record.fieldsInfo[this.viewType][fieldName].Widget;
        var widget = new Widget(this, fieldName, record, _.extend({
            mode: modifiers.readonly ? 'readonly' : this.mode,
            viewType: this.viewType,
        }, options || {}));

        // Register the widget so that it can easily be found again
        if (this.allFieldWidgets[record.id] === undefined) {
            this.allFieldWidgets[record.id] = [];
        }
        this.allFieldWidgets[record.id].push(widget);

        widget.__node = node; // TODO get rid of this if possible one day

        // Prepare widget rendering and save the related deferred
        var def = widget.__widgetRenderAndInsert(function () {});
        if (def.state() === 'pending') {
            this.defs.push(def);
        }

        // Update the modifiers registration by associating the widget and by
        // giving the modifiers options now (as the potential callback is
        // associated to new widget)
        this._registerModifiers(node, record, widget, modifiersOptions);

        return widget;
    },
    /**
     * Actual rendering. Supposed to be overridden by concrete renderers.
     * The basic responsabilities of _renderView are:
     * - use the xml arch of the view to render a jQuery representation
     * - instantiate a widget from the registry for each field in the arch
     *
     * Note that the 'state' field should contains all necessary information
     * for the rendering. The field widgets should be as synchronous as
     * possible.
     *
     * @abstract
     * @returns {Deferred}
     */
    _renderView: function () {
        return $.when();
    },
    /**
     * Rerenders a given widget and make sure the associated data which
     * referenced the old one is updated.
     *
     * @private
     * @param {Widget} widget
     * @param {Object} record
     * @returns {AbstractField}
     */
    _rerenderFieldWidget: function (widget, record) {
        // Render the new field widget
        var newWidget = this._renderFieldWidget(widget.__node, record);
        widget.$el.replaceWith(newWidget.$el);

        // Destroy the old widget and position the new one at the old one's
        var oldIndex = this._destroyFieldWidget(record, widget);
        var recordWidgets = this.allFieldWidgets[record.id];
        recordWidgets.splice(oldIndex, 0, newWidget);
        recordWidgets.pop();

        return newWidget;
    },
    /**
     * Unregisters an element of the modifiers data associated to the given
     * node and record.
     *
     * @param {Object} node
     * @param {Object} record
     * @param {jQuery|AbstractField} element
     */
    _unregisterModifiersElement: function (node, record, element) {
        var modifiersData = this._getModifiersData(node);
        if (modifiersData) {
            var elements = modifiersData.elementsByRecord[record.id];
            var index = _.findIndex(elements, function (oldElement) {
                return oldElement.widget === element
                    || oldElement.$el[0] === element[0];
            });
            if (index >= 0) {
                elements.splice(index, 1);
            }
        }
    },
    /**
     * Does two actions, for each registered modifiers:
     * 1) Recomputes the modifiers associated to the given record and saves them
     *    (as boolean values) in the appropriate modifiers data.
     * 2) Updates the rendering of the view elements associated to the given
     *    record to match the new modifiers.
     *
     * @see _computeModifiers
     * @see _applyModifiers
     *
     * @private
     * @param {Object} record
     * @returns {Deferred} resolved once finished
     */
    _updateAllModifiers: function (record) {
        var self = this;

        var defs = [];
        this.defs = defs; // Potentially filled by widget rerendering
        _.each(this.allModifiersData, function (modifiersData) {
            self._computeModifiers(modifiersData, record);
            self._applyModifiers(modifiersData, record);
        });
        delete this.defs;

        return $.when.apply($, defs);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When someone presses TAB in a widget, it is nice to be able to go to the
     * next widget, especially since the TAB key event is preventDefaulted
     *
     * @abstract
     * @private
     * @param {OdooEvent} ev
     */
    _onMoveNext: function (ev) {},
    /**
     * When someone presses SHIFT+TAB in a widget, it is nice to be able to go
     * back to the previous widget, especially since the TAB key event is
     * preventDefaulted
     *
     * @abstract
     * @private
     * @param {OdooEvent} ev
     */
    _onMovePrevious: function (ev) {},
});

return BasicRenderer;
});
