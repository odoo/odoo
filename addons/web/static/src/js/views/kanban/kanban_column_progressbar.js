odoo.define('web.KanbanColumnProgressBar', function (require) {
'use strict';

var Widget = require('web.Widget');
var session = require('web.session');
var utils = require('web.utils');

var KanbanColumnProgressBar = Widget.extend({
    template: 'KanbanView.ColumnProgressBar',
    events: {
        'click .o_kanban_counter_progress': '_onProgressBarParentClick',
        'click .progress-bar': '_onProgressBarClick',
    },
    /**
     * Allows to disable animations for tests.
     * @type {boolean}
     */
    ANIMATE: true,

    /**
     * @constructor
     */
    init: function (parent, options, columnState) {
        this._super.apply(this, arguments);

        this.columnID = options.columnID;

        // <progressbar/> attributes
        this.fieldName = columnState.progressBarValues.field;
        this.colors = columnState.progressBarValues.colors;
        this.sumField = columnState.progressBarValues.sum;

        // Previous progressBar state
        var state = options.progressBarStates[this.columnID];
        this.groupCount = state ? state.groupCount : 0;
        this.subgroupCounts = state ? state.subgroupCounts : {};
        this.totalCounterValue = state ? state.totalCounterValue : 0;
        this.activeFilter = state ? state.activeFilter : false;

        // Prepare currency (TODO this should be automatic... use a field ?)
        this.counterPrefix = '';
        this.counterSuffix = '';
        var sumFieldInfo = this.sumField && columnState.fieldsInfo.kanban[this.sumField];
        var currencyField = sumFieldInfo && sumFieldInfo.options && sumFieldInfo.options.currency_field;
        if (currencyField && columnState.data.length) {
            var currency = session.currencies[columnState.data[0].data[currencyField].res_id];
            if (currency.position === 'before') {
                this.counterPrefix = currency.symbol + ' ';
            } else {
                this.counterSuffix = ' ' + currency.symbol;
            }
        }
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        this.$bars = {};
        _.each(this.colors, function (val, key) {
            self.$bars[val] = self.$('.bg-' + val + '-full');
        });
        this.$counter = this.$('.o_kanban_counter_side');

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Updates internal data and rendering according to new received column
     * state.
     *
     * @param {Object} columnState
     */
    update: function (columnState) {
        var self = this;

        var subgroupCounts = {};
        _.each(self.colors, function (val, key) {
            var subgroupCount = columnState.progressBarValues.counts[key] || 0;
            if (self.activeFilter === val && subgroupCount === 0) {
                self.activeFilter = false;
            }
            subgroupCounts[key] = subgroupCount;
        });

        this.groupCount = columnState.count;
        this.subgroupCounts = subgroupCounts;
        this.prevTotalCounterValue = this.totalCounterValue;
        this.totalCounterValue = this.sumField ? (columnState.aggregateValues[this.sumField] || 0) : columnState.count;
        this._notifyState();
        this._render();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Updates the rendering according to internal data. This is done without
     * qweb rendering because there are animations.
     *
     * @private
     */
    _render: function () {
        var self = this;

        // Update column display according to active filter
        this.trigger_up('tweak_column', {
            callback: function ($el) {
                $el.removeClass('o_kanban_group_show');
                _.each(self.colors, function (val, key) {
                    $el.removeClass('o_kanban_group_show_' + val);
                });
                if (self.activeFilter) {
                    $el.addClass('o_kanban_group_show o_kanban_group_show_' + self.colors[self.activeFilter]);
                }
            },
        });
        this.trigger_up('tweak_column_records', {
            callback: function ($el, recordData) {
                var categoryValue = recordData[self.fieldName];
                _.each(self.colors, function (val, key) {
                    $el.removeClass('oe_kanban_card_' + val);
                });
                if (self.colors[categoryValue]) {
                    $el.addClass('oe_kanban_card_' + self.colors[categoryValue]);
                }
            },
        });

        // Display and animate the progress bars
        _.each(self.colors, function (val, key) {
            var $bar = self.$bars[val];
            var count = self.subgroupCounts[key];

            if (!$bar) {
                return;
            }

            // Adapt tooltip
            $bar.attr('data-original-title', count + ' ' + key);
            $bar.tooltip({
                delay: '0',
                trigger:'hover',
                placement: 'top'
            });

            // Adapt active state
            $bar.toggleClass('active progress-bar-striped', key === self.activeFilter);

            // Adapt width
            $bar.removeClass('o_bar_has_records transition-off');
            window.getComputedStyle($bar[0]).getPropertyValue('width'); // Force reflow so that animations work
            if (count > 0) {
                $bar.addClass('o_bar_has_records');
                $bar.css('width', (count * 100 / self.groupCount) + '%');
            } else {
                $bar.css('width', '');
            }
        });

        // Display and animate the counter number
        var humanNumber;
        var suffix = this.counterSuffix;
        var end = this.totalCounterValue;
        if (end >= 10000) {
            humanNumber = utils.human_number(end, 1);
            end = parseFloat(humanNumber.substr(0, humanNumber.length - 1));
            suffix = humanNumber[humanNumber.length - 1] + suffix;
        }
        var start = this.prevTotalCounterValue || 0;
        if (start >= 10000) {
            humanNumber = utils.human_number(start, 1);
            start = parseFloat(humanNumber.substr(0, humanNumber.length - 1));
        }
        if (end > start && this.ANIMATE) {
            $({currentValue: start}).animate({currentValue: end}, {
                duration: 1000,
                start: function () {
                    self.$counter.addClass('o_kanban_grow');
                },
                step: function () {
                    self.$counter.html(self.counterPrefix + Math.round(this.currentValue) + suffix);
                },
                complete: function () {
                    self.$counter.html(self.counterPrefix + this.currentValue + suffix);
                    self.$counter.removeClass('o_kanban_grow');
                },
            });
        } else {
            this.$counter.html(this.counterPrefix + end + suffix);
        }
    },
    /**
     * Notifies the new progressBar state so that if a full rerender occurs, the
     * new progressBar that would replace this one will be initialized with
     * current state, so that animations are correct.
     *
     * @private
     */
    _notifyState: function () {
        this.trigger_up('set_progress_bar_state', {
            columnID: this.columnID,
            values: {
                groupCount: this.groupCount,
                subgroupCounts: this.subgroupCounts,
                totalCounterValue: this.totalCounterValue,
                activeFilter: this.activeFilter,
            },
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onProgressBarClick: function (ev) {
        this.$clickedBar = $(ev.currentTarget);
        var filter = this.$clickedBar.data('filter');
        this.activeFilter = (this.activeFilter === filter ? false : filter);
        this._notifyState();
        this._render();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onProgressBarParentClick: function (ev) {
        if (ev.target !== ev.currentTarget) {
            return;
        }
        this.activeFilter = false;
        this._notifyState();
        this._render();
    },
});
return KanbanColumnProgressBar;
});
