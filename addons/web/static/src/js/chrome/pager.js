odoo.define('web.Pager', function (require) {
"use strict";

var utils = require('web.utils');
var Widget = require('web.Widget');

var direction = {
    previous: -1,
    next: 1,
};

var Pager = Widget.extend({
    template: "Pager",
    events: {
        'click .o_pager_next': '_onNext',
        'click .o_pager_previous': '_onPrevious',
        'click .o_pager_value': '_onEdit',
    },
    /**
     * The pager goes from 1 to size (included).
     * The current value is current_min if limit === 1
     *          or the interval [current_min, current_min + limit[ if limit > 1
     *
     * @param {Widget} [parent] the parent widget
     * @param {int} [size] the total number of elements
     * @param {int} [current_min] the first element of the current_page
     * @param {int} [limit] the number of elements per page
     * @param {boolean} [options.can_edit] editable feature of the pager
     * @param {boolean} [options.single_page_hidden] (not) to display the pager
     *   if only one page
     * @param {function} [options.validate] callback returning a Deferred to
     *   validate changes
     */
    init: function (parent, size, current_min, limit, options) {
        this.state = {
            size: size,
            current_min: current_min,
            limit: limit,
        };
        Object.defineProperty(this.state, 'current_max', {
            get: function() {
                return Math.min(this.current_min + this.limit - 1, this.size);
            }
        });
        this.options = _.defaults({}, options, {
            can_edit: true, // editable
            single_page_hidden: false, // displayed even if there is a single page
            validate: function() {
                return $.Deferred().resolve();
            },
            withAccessKey: true,  // can be disabled, for example, for x2m widgets
        });
        this._super(parent);
    },
    /**
     * Renders the pager
     *
     * @returns {jQuery.Deferred}
     */
    start: function () {
        this.$value = this.$('.o_pager_value');
        this.$limit = this.$('.o_pager_limit');
        this._render();
        return this._super();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Disables the pager's arrows and the edition
     */
    disable: function () {
        this.disabled = true;
        this._updateArrows();
    },
    /**
     * Enables the pager's arrows and the edition
     */
    enable: function () {
        this.disabled = false;
        this._updateArrows();
    },
    /**
     * Executes the next action on the pager
     */
    next: function () {
        this._changeSelection(direction.next);
    },
    /**
     * Executes the previous action on the pager
     */
    previous: function () {
        this._changeSelection(direction.previous);
    },
    /**
     * Sets the state of the pager and renders it
     * @param {Object} [state] the values to update (size, current_min and limit)
     * @param {Object} [options]
     * @param {boolean} [options.notifyChange] set to true to make the pager
     *   notify the environment that its state changed
     */
    updateState: function (state, options) {
        _.extend(this.state, state);
        this._render();
        if (options && options.notifyChange) {
            this.trigger('pager_changed', _.clone(this.state));
        }
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Private function that updates the pager's state according to a pager action
     *
     * @param {int} [direction] the action (previous or next) on the pager
     */
    _changeSelection: function (direction) {
        var self = this;
        this.options.validate().then(function() {
            var size = self.state.size;
            var current_min = self.state.current_min;
            var limit = self.state.limit;

            // Compute the new current_min
            current_min = (current_min + limit*direction);
            if (current_min > size) {
                current_min = 1;
            } else if ((current_min < 1) && (limit === 1)) {
                current_min = size;
            } else if ((current_min < 1) && (limit > 1)) {
                current_min = size - ((size % limit) || limit) + 1;
            }

            self.state.current_min = current_min;
            // The re-rendering of the pager must be done before the trigger of
            // event 'pager_changed' as the rendering may enable the pager
            // (and a common use is to disable the pager when this event is
            // triggered, and to re-enable it when the data have been reloaded)
            self._render();
            self.trigger('pager_changed', _.clone(self.state));
        });
    },
    /**
     * Private function that displays an input to edit the pager's state
     */
    _edit: function () {
        if (this.options.can_edit) {
            var self = this;
            var $input = $('<input>', {class: 'o_input', type: 'text', value: this.$value.html()});

            this.$value.html($input);
            $input.focus();

            // Event handlers
            $input.click(function(ev) {
                ev.stopPropagation(); // ignore clicks on the input
            });
            $input.blur(function(ev) {
                self._save($(ev.target)); // save the state when leaving the input
            });
            $input.on('keydown', function (ev) {
                ev.stopPropagation();
                if (ev.which === $.ui.keyCode.ENTER) {
                    self._save($(ev.target)); // save on enter
                } else if (ev.which === $.ui.keyCode.ESCAPE) {
                    self._render(); // leave on escape
                }
            });
        }
    },
    /**
     * Private function that renders the pager's state
     */
    _render: function () {
        var size = this.state.size;
        var current_min = this.state.current_min;
        var current_max = this.state.current_max;

        if (size === 0 || (this.options.single_page_hidden && this._singlePage())) {
            this.do_hide();
        } else {
            this.do_show();
            this._updateArrows();

            var value = "" + current_min;
            if (this.state.limit > 1) {
                value += "-" + current_max;
            }
            this.$value.html(value);
            this.$limit.html(size);
        }
    },
    /**
     * Private function that saves the state from the content of the input
     *
     * @param {jQuery} [$input] the jQuery element containing the new state
     */
    _save: function ($input) {
        var self = this;
        this.options.validate().then(function() {
            var value = $input.val().split("-");
            var min = utils.confine(parseInt(value[0], 10), 1, self.state.size);
            var max = utils.confine(parseInt(value[1], 10), 1, self.state.size);

            if (!isNaN(min)) {
                self.state.current_min = min;
                if (!isNaN(max)) {
                    self.state.limit = utils.confine(max-min+1, 1, self.state.size);
                } else {
                    // The state has been given as a single value -> set the limit to 1
                    self.state.limit = 1;
                }
                self.trigger('pager_changed', _.clone(self.state));
            }
        }).always(function() {
            // Render the pager's new state (removes the input)
            self._render();
        });
    },
    /**
     * @private
     * @returns {boolean} true iff there is only one page
     */
    _singlePage: function () {
        var state = this.state;
        return (1 === state.current_min) && (state.current_max === state.size);
    },
    /**
     * Updates the arrows' disable attribute: true iff the pager is disabed or
     * if there is only one page
     *
     * @private
     */
    _updateArrows: function () {
        var disabled = this.disabled || this._singlePage();
        this.$('button').prop('disabled', disabled);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} event
     */
    _onEdit: function (event) {
        event.stopPropagation();
        if (!this.disabled) {
            this._edit();
        }
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onNext: function (event) {
        event.stopPropagation();
        this.next();
    },
    /**
     * @private
     * @param {MouseEvent} event
     */
    _onPrevious: function (event) {
        event.stopPropagation();
        this.previous();
    },
});

return Pager;

});
