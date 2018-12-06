odoo.define('web.TimeRangeMenu', function (require) {
"use strict";

var config = require('web.config');
var controlPanelViewParameters = require('web.controlPanelViewParameters');
var Widget = require('web.Widget');

var COMPARISON_TIME_RANGE_OPTIONS = controlPanelViewParameters.COMPARISON_TIME_RANGE_OPTIONS;
var PERIOD_OPTIONS = controlPanelViewParameters.PERIOD_OPTIONS;

var TimeRangeMenu = Widget.extend({
    template: 'web.TimeRangeMenu',
    events: {
        'click .o_apply_range': '_onApplyButtonClick',
        'click .o_comparison_checkbox': '_onCheckBoxClick',
    },
    /**
     * @override
     * @param {Widget} parent
     * @param {Object[]} timeRanges
     *
     */
    init: function (parent, timeRanges) {
        this._super.apply(this, arguments);
        // determine header style
        this.isMobile = config.device.isMobile;
        this.symbol = this.isMobile ? 'fa fa-chevron-right float-right mt4' : 'caret';
        // fixed parameters
        this.periodOptions = PERIOD_OPTIONS;
        this.comparisonTimeRangeOptions = COMPARISON_TIME_RANGE_OPTIONS;
        this.periodGroups = _.uniq(PERIOD_OPTIONS.map(function (option) {
            return option.groupId;
        }));
        // variable parameters
        this.timeRanges = timeRanges;
        this.configuration = {
            comparisonIsSelected: false,
            comparisonTimeRangeId: false,
            id: false,
            timeRangeId: false,
        };
        this._configure();
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {Object[]} timeRanges
     */
    update: function (timeRanges) {
        this.timeRanges = timeRanges;
        this._configure();
        this.renderElement();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _configure: function () {
        this.configuration = this.timeRanges.find(function (timeRange) {
            return timeRange.isActive;
        }) || this.configuration;
        this.configuration.comparisonIsSelected = !!this.configuration.comparisonTimeRangeId;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onApplyButtonClick: function () {
        var id = this.$('.o_date_field_selector').val();
        var timeRangeId = this.$('.o_time_range_selector').val();
        var comparisonTimeRangeId = false;
        if (this.configuration.comparisonIsSelected) {
            comparisonTimeRangeId = this.$('.o_comparison_time_range_selector').val();
        }
        this.trigger_up('activate_time_range', {
            id: id,
            timeRangeId: timeRangeId,
            comparisonTimeRangeId: comparisonTimeRangeId
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onCheckBoxClick: function (ev) {
        ev.stopPropagation();
        this.configuration.comparisonIsSelected = this.$('.o_comparison_checkbox').prop('checked');
        this.$('.o_comparison_time_range_selector').toggleClass('o_hidden');
        this.$el.addClass('open');
    }
});

return TimeRangeMenu;

});
