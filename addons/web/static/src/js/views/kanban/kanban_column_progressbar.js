odoo.define('web.KanbanColumnProgressBar', function (require) {
'use strict';

const core = require('web.core');
var session = require('web.session');
var utils = require('web.utils');
var Widget = require('web.Widget');

const _t = core._t;

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
        this.columnState = columnState;

        // <progressbar/> attributes
        this.fieldName = columnState.progressBarValues.field;
        this.colors = _.extend({}, columnState.progressBarValues.colors, {
            __false: 'muted', // color to use for false value
        });
        this.sumField = columnState.progressBarValues.sum_field;

        // Previous progressBar state
        var state = options.progressBarStates[this.columnID];
        if (state) {
            this.groupCount = state.groupCount;
            this.subgroupCounts = state.subgroupCounts;
            this.totalCounterValue = state.totalCounterValue;
            this.activeFilter = state.activeFilter;
        }

        // Prepare currency (TODO this should be automatic... use a field ?)
        var sumFieldInfo = this.sumField && columnState.fieldsInfo.kanban[this.sumField];
        var currencyField = sumFieldInfo && sumFieldInfo.options && sumFieldInfo.options.currency_field;
        if (currencyField && columnState.data.length) {
            this.currency = session.currencies[columnState.data[0].data[currencyField].res_id];
        }
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        this.$bars = {};
        _.each(this.colors, function (val, key) {
            self.$bars[key] = self.$(`.progress-bar[data-filter=${key}]`);
        });
        this.$counter = this.$('.o_kanban_counter_side');
        this.$number = this.$counter.find('b');

        if (this.currency) {
            var $currency = $('<span/>', {
                text: this.currency.symbol,
            });
            if (this.currency.position === 'before') {
                $currency.prependTo(this.$counter);
            } else {
                $currency.appendTo(this.$counter);
            }
        }

        return this._super.apply(this, arguments).then(function () {
            // This should be executed when the progressbar is fully rendered
            // and is in the DOM, this happens to be always the case with
            // current use of progressbars

            var subgroupCounts = {};
            let allSubgroupCount = 0;
            _.each(self.colors, function (val, key) {
                var subgroupCount = self.columnState.progressBarValues.counts[key] || 0;
                if (self.activeFilter === key && subgroupCount === 0) {
                    self.activeFilter = false;
                }
                subgroupCounts[key] = subgroupCount;
                allSubgroupCount += subgroupCount;
            });
            subgroupCounts.__false = self.columnState.count - allSubgroupCount;

            self.groupCount = self.columnState.count;
            self.subgroupCounts = subgroupCounts;
            self.prevTotalCounterValue = self.totalCounterValue;
            self.totalCounterValue = self.sumField ? (self.columnState.aggregateValues[self.sumField] || 0) : self.columnState.count;

            self._notifyState();
            self._render();
        });
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
                var categoryValue = recordData[self.fieldName] ? recordData[self.fieldName] : '__false';
                _.each(self.colors, function (val, key) {
                    $el.removeClass('oe_kanban_card_' + val);
                });
                if (self.colors[categoryValue]) {
                    $el.addClass('oe_kanban_card_' + self.colors[categoryValue]);
                }
            },
        });

        // Display and animate the progress bars
        var barNumber = 0;
        var barMinWidth = 6; // In %
        const selection = self.columnState.fields[self.fieldName].selection;
        _.each(self.colors, function (val, key) {
            var $bar = self.$bars[key];
            var count = self.subgroupCounts && self.subgroupCounts[key] || 0;

            if (!$bar) {
                return;
            }

            // Adapt tooltip
            let value;
            if (selection) { // progressbar on a field of type selection
                const option = selection.find(option => option[0] === key);
                value = option && option[1] || _t('Other');
            } else {
                value = key;
            }
            $bar.attr('data-original-title', count + ' ' + value);
            $bar.tooltip({
                delay: 0,
                trigger: 'hover',
            });

            // Adapt active state
            $bar.toggleClass('progress-bar-animated progress-bar-striped', key === self.activeFilter);

            // Adapt width
            $bar.removeClass('o_bar_has_records transition-off');
            window.getComputedStyle($bar[0]).getPropertyValue('width'); // Force reflow so that animations work
            if (count > 0) {
                $bar.addClass('o_bar_has_records');
                // Make sure every bar that has records has some space
                // and that everything adds up to 100%
                var maxWidth = 100 - barMinWidth * barNumber;
                self.$('.progress-bar.o_bar_has_records').css('max-width', maxWidth + '%');
                $bar.css('width', (count * 100 / self.groupCount) + '%');
                barNumber++;
                $bar.attr('aria-valuemin', 0);
                $bar.attr('aria-valuemax', self.groupCount);
                $bar.attr('aria-valuenow', count);
            } else {
                $bar.css('width', '');
            }
        });
        this.$('.progress-bar.o_bar_has_records').css('min-width', barMinWidth + '%');

        // Display and animate the counter number
        var start = this.prevTotalCounterValue;
        var end = this.totalCounterValue;

        if (this.activeFilter) {
            if (this.sumField) {
                end = 0;
                _.each(self.columnState.data, function (record) {
                    var recordData = record.data;
                    if (self.activeFilter === recordData[self.fieldName] ||
                        (self.activeFilter === '__false' && !recordData[self.fieldName])) {
                        end += parseFloat(recordData[self.sumField]);
                    }
                });
            } else {
                end = this.subgroupCounts[this.activeFilter];
            }
        }
        this.prevTotalCounterValue = end;
        var animationClass = start > 999 ? 'o_kanban_grow' : 'o_kanban_grow_huge';

        if (start !== undefined && (end > start || this.activeFilter) && this.ANIMATE) {
            $({currentValue: start}).animate({currentValue: end}, {
                duration: 1000,
                start: function () {
                    self.$counter.addClass(animationClass);
                },
                step: function () {
                    self.$number.html(_getCounterHTML(this.currentValue));
                },
                complete: function () {
                    self.$number.html(_getCounterHTML(this.currentValue));
                    self.$counter.removeClass(animationClass);
                },
            });
        } else {
            this.$number.html(_getCounterHTML(end));
        }

        function _getCounterHTML(value) {
            return utils.human_number(value, 0, 3);
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
