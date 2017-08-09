odoo.define('kanban.progressBar', function (require) {
"use strict";

var Widget = require('web.Widget');
var session = require('web.session');


var ColumnProgressBar =  Widget.extend({
    template: 'KanbanView.ProgressBar',
    events: {
        'click .progress-bar': '_onProgressBarClick',
        'click .o_kanban_counter_progress': '_oncounterProgressBarClick'
    },

    init: function (parent, barOptions, fieldsInfo, header) {
        this._super.apply(this, arguments);
        this.sumField = barOptions.attrs.sum;
        this.fieldName = barOptions.attrs.field;
        this.counterModel = barOptions.counterModel;
        this.dataRecords = barOptions.dataRecords;
        this.colors = JSON.parse(barOptions.attrs.colors);
        this.currencyPrefix = "";
        this.currencySuffix = "";
        this.isMonetary = false;
        this.$header = header;
        this.columnId = barOptions.columnId;
        this.counterModel.setCounter({
            columnId: this.columnId,
            dataRecords: this.dataRecords
        });
        var model = this.counterModel.getCounter({
            columnId: this.columnId,
            dataRecords: this.dataRecords
        });
        this.totalCounterValue = model.counter;
        this.activeCurrencyId = model.activeCurrencyId;
        this.moreAnimation = model.animationVal;

        if (this.sumField && fieldsInfo[this.sumField].widget == 'monetary') {
            this.isMonetary = true;
            this.getCurrency();
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Remove All the o_kanban_group_show_ class from Kanban_group
     *
     * @param {object} $el Kanban_group class object
     */
    removeAllClass: function($el) {
        _.each(this.colors, function(val, key){
            $el.removeClass('o_kanban_group_show_'+ val);
        });
        $el.removeClass('o_kanban_group_show');
    },
    /**
     * Uses to initialize the current active currency
     */
    getCurrency: function () {
        if (this.isMonetary && this.dataRecords.length > 0) {
            if (session.currencies[this.activeCurrencyId].position === 'before') {
                this.currencyPrefix = session.currencies[this.activeCurrencyId].symbol + " ";
            } else {
                this.currencySuffix = " " + session.currencies[this.activeCurrencyId].symbol;
            }
        }
    },
    /**
     * Counting the Value of all KanbanProgressBar, calling _animateTotal Function and setting the proper
     * width of all ProgressBar.
     * @param {object} records kanban records
     */
    progressCounter: function (records) {
        var self = this;
        this.result = {};
        this.progressVal = {};
        this.progressVal[this.columnId] = {};
        var isLastRecord = false;

        $(records).each(function () {
            var groupField = this.state.data[self.fieldName];
            if (!self.result[groupField]) {
                self.result[groupField] = {
                    val: 0,
                    count: 0
                };
            }
            var data = self.result[groupField];
            if (self.sumField) {
                data.val += this.state.data[self.sumField];
            } else {
                data.val += 1;
            }
            data.count += 1;
            if (self.colors[groupField]) {
                this.$el.addClass('oe_kanban_card_'+ self.colors[groupField]);
            }
        });
        var sumCount = _.reduce(self.result, function(sum, data){ return sum + data.count;}, 0);

        //Decreasing the width of element who has previosly 100% width.
        if (this.lastProgressResult) {
            _.each(this.colors, function (val, key) {
                var dataVals = self.result[key] ? self.result[key].count : 0;
                var lastBarWidth = self.lastProgressResult[key] ? (self.lastProgressResult[key].count / self.lastProgressResult[key].sumCount)*100 : 0;
                if (self['$bar_'+val].length && lastBarWidth == 100 ) {
                    dataVals > 0 ? self['$bar_'+val].width((dataVals / sumCount) * 100 + "%").addClass('o_bar_active').removeClass('transition-off') : self['$bar_'+val].width(0).removeClass('active o_bar_active transition-off progress-bar-striped');
                } else if (self.$kanban_group.hasClass('o_kanban_group_show') && dataVals === 0) {
                    isLastRecord = true;
                }
            });
        }
        this._animateTotal(this.$kanban_group.data('state'), !isLastRecord);
        //To provide proper time in decresing process of ProgressBar.To avoide flickering problem.
        setTimeout(function(){
            _.each(self.colors, function (val, key) {
                var dataVals = self.result[key] ? self.result[key].count : 0;
                if (self['$bar_'+val].length) {
                    if (dataVals > 0) {
                        self['$bar_'+val].width((dataVals / sumCount) * 100 + "%").addClass('o_bar_active').removeClass('transition-off');
                    } else {
                        self['$bar_'+val].width(0).removeClass('active o_bar_active transition-off progress-bar-striped');
                    }
                }
                self.progressVal[self.columnId][key] = {
                    count: self.result[key] ? self.result[key].count : 0,
                    sumCount: sumCount || 0
                };
            });
        },100);
        this.counterModel.setCounter({
            progressVal: this.progressVal,
            columnId: self.columnId
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Method responsible to animate and display the ProgressBar Counter Number.
     * @param {integer} end value
     * @param {object} $el Side Counter Object
     * @param {integer} duration of animation
     * @param {string} prefix To apply prefix to side counter
     * @param {string} suffix To apply suffix to side counter
     */
    _animateNumber: function (end, $el, duration, prefix, suffix) {
        suffix = suffix || "";
        prefix = prefix || "";
        var start = this.totalCounterValue;
        this.counterModel.setCounter({
            value: end,
            columnId: this.columnId
        });

        if (end > 1000000) {
            end = end / 1000000;
            suffix = "M " + suffix;
        }
        else if (end > 1000) {
            end = end / 1000;
            suffix = "K " + suffix;
        }
        if (start > 1000000) {
            start = start / 1000000;
        }
        else if (start > 1000) {
            start = start / 1000;
        }

        var progressBarLength = (90 - (2.8)*parseInt(end).toString().length).toString() + '%';
        this.$('.o_kanban_counter_progress').animate({width: progressBarLength}, 300);
        if (end > start) {
            if ($.inArray(this.columnId, this.moreAnimation) != -1 && end > 80){
                duration = 2500;
            }
            $({ someValue: start}).animate({ someValue: end || 0 }, {
                duration: duration,
                easing: 'swing',
                step: function () {
                    $el.html(prefix + Math.round(this.someValue) + suffix);
                },
                complete: function () {
                    $el.removeClass('o-kanban-grow');
                }
            });

            //for sync between Grow effect and Number increment effect
            setTimeout(function (){
                $el.addClass('o-kanban-grow');
            },200);
        } else {
            $el.html(prefix + Math.round(end || 0) + suffix);
        }
    },
    /**
     * Method uses to call the _animateNumber method, depending upon the progressBar filter condition.
     *
     * @param {string} state progressBar Class name
     * @param {Boolean} isReverse true/false
     */
    _animateTotal: function (state, isReverse) {
        var isToggle = this.$kanban_group.is('.o_kanban_group_show_'+this.colors[state]);
        isToggle = isReverse ? !isToggle : isToggle;
        this.removeAllClass(this.$kanban_group);
        if(isToggle){
            var sum = _.reduce(this.result, function(sum, data){ return sum + data.val || 0;}, 0);
            this._animateNumber(sum, this.$side_c, 1000, this.currencyPrefix, this.remaining > 0 ? this.currencyPrefix+"+":this.currencySuffix);
        } else if (this.result[state]) {
            this._animateNumber(this.result[state].val, this.$side_c, 1000, this.currencyPrefix, this.currencySuffix);
            this.$kanban_group.toggleClass('o_kanban_group_show_'+this.colors[state]).toggleClass('o_kanban_group_show');
            this.$kanban_group.data('state', state);
        }
        if (!isReverse) {
            this.clickedBar.toggleClass('active progress-bar-striped').siblings().removeClass('active progress-bar-striped');
        }
    },
    /**
     * Method responsible to set the attribute in ProgressBar to show hover tooltip.
     */
    _barAttrs: function () {
        var self = this;
        _.each(this.result, function (val, key) {
            var dataVals = self['bar_n_'+self.colors[key]];
            dataVals = self.result[key].count;
            if (self['$bar_'+self.colors[key]]) {
                self['$bar_'+self.colors[key]].attr({
                    'data-original-title': dataVals +' '+key,
                    'data-state': key
                });
                self['$bar_'+self.colors[key]].tooltip({
                    delay: '0',
                    trigger:'hover',
                    placement: 'top'
                });
            }
        });
    },
    /**
     * Method for affixing the element to top content.
     * @param {object} $el element to affix to top.
     */
    _fixBarPosition: function ($el) {
        $el.affix({
            offset: {
                top: function () {
                    return 2;
                }
            },
            target: $('.o_content'),
        });
    },
    /**
     * Method Responsible to re-initialize kanban ProgressBar and for setting default width to ProgressBar
     * Method calls when update on any kanban record happens.Gets trigger from web.KanbanRecord widget.
     * @param {object} records kanban records.
     * @param {integer} remaining number of records(if >80).
     */
    _update: function (records, remaining) {
        this.$kanban_group = this.$el.closest('.o_kanban_group');
        this.$side_c = this.$('.o_kanban_counter_side');
        this.$counter = this.$('.o_kanban_counter_progress');
        var self = this;
        $('<div/>', {class: 'o_progressBar_ghost'}).insertAfter(this.$el);

        _.each(this.colors, function (val, key) {
            var $div_color;
            if (self.$('.o_progress_'+val).length) {
                $div_color = self.$('.o_progress_'+val);
            } else {
                $div_color = $('<div/>', {class: 'progress-bar transition-off o_progress_'+val});
                self.$('.o_kanban_counter_progress').append($div_color);
            }
            self['$bar_'+val] = $div_color;
            self['bar_n_'+val] = 0;
        });

        this.remaining = remaining;
        if (this.remaining) {
            if ($.inArray(this.columnId, this.moreAnimation) === -1) {
                this.counterModel.setCounter({
                    animationVal: this.columnId
                });
            }
        }
        this.records = records;

        var model = this.counterModel.getCounter({
            columnId: this.columnId,
            dataRecords: this.dataRecords
        });
        this.totalCounterValue = model.counter;
        this.activeCurrencyId = model.activeCurrencyId;
        this.lastProgressResult = model.progressVal;

        //Applying Default lastwidth to the progressBar without animation.
        _.each(this.lastProgressResult, function (val, key) {
            if (self['$bar_'+self.colors[key]]) {
                self['$bar_'+self.colors[key]].width((val.count / val.sumCount) * 100 + "%");
            }
        });

        // In xml template data-delay of 500 ms is given so to work affixBar properly
        // we require to apply time delay of 500 ms.
        setTimeout(function(){
            self._fixBarPosition(self.$header);
            self._fixBarPosition(self.$el);
        }, 500);
        this.progressCounter(this.records);
        this._barAttrs();
        this.removeAllClass(this.$el);
    },

    //--------------------------------------------------------------------------
    // Handelers
    //--------------------------------------------------------------------------

    /**
     * @param {OdooEvent} event
     */
    _onProgressBarClick: function (e) {
        $('.o_content').scrollTop(0);
        this.clickedBar = $(e.currentTarget);
        var state = this.clickedBar.data('state');
        this._animateTotal(state, false);
    },
    /**
     * @param {OdooEvent} event
     */
    _oncounterProgressBarClick: function (e) {
        if ($(e.target).hasClass('o_kanban_counter_progress')) {
            if (this.$el.parent().hasClass('o_kanban_group_show')) {
                var state = this.clickedBar.data('state');
                this['$bar_'+this.colors[state]].trigger('click');
            }
        }
    },
});


return ColumnProgressBar;

});
