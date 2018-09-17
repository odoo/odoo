odoo.define('web.TimeRangeMenu', function (require) {
"use strict";

var config = require('web.config');
var core = require('web.core');
var Domain = require('web.Domain');
var TimeRangeMenuOptions = require('web.TimeRangeMenuOptions');
var Widget = require('web.Widget');

var _t = core._t;
var ComparisonOptions = TimeRangeMenuOptions.ComparisonOptions;
var PeriodOptions = TimeRangeMenuOptions.PeriodOptions;

var TimeRangeMenu = Widget.extend({
    template: 'web.TimeRangeMenu',
    events: {
        'click .o_apply_range': '_onApplyButtonClick',
        'click .o_comparison_checkbox': '_onCheckBoxClick',
    },

    /**
     * override
     * @param {Widget} parent
     * @param {Object} fields
     * @param {Object} configuration
     *
     */
    init: function(parent, fields, configuration) {
        var self = this;
        this.isMobile = config.device.isMobile;
        this.symbol = this.isMobile ? 'fa fa-chevron-right float-right mt4' : 'caret';
        this._super(parent);
        this.dateFields = [];
        _.each(fields, function (field, name) {
            if (field.sortable && _.contains(['date', 'datetime'], field.type)) {
                self.dateFields.push(_.extend({}, field, {
                    name: name,
                }));
            }
        });
        this.periodOptions = PeriodOptions;
        this.periodGroups = PeriodOptions.reduce(
            function (acc, option) {
                if (!_.contains(acc, option.groupId)) {
                    acc.push(option.groupId);
                }
                return acc;
            },
            []
        );

        this.comparisonOptions = ComparisonOptions;

        // Following steps determine initial configuration
        this.isActive = false;
        this.timeRangeId = undefined;
        this.comparisonIsSelected = false;
        this.comparisonTimeRangeId = undefined;
        this.dateField = {};
        if (configuration && configuration.field && configuration.range) {
            this.isActive = true;
            var dateField = _.findWhere(this.dateFields, {name: configuration.field});
            this.dateField = {
                name: dateField.name,
                description: dateField.string,
                type: dateField.type,
            };
            this.timeRangeId = configuration.range;
            if (configuration.comparison_range) {
                this.comparisonIsSelected = true;
                this.comparisonTimeRangeId = configuration.comparison_range;
            }
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    deactivate: function () {
        this.isActive = false;
        this.comparisonIsSelected = false;
        this.renderElement();
    },
    /**
     * Generates a :js:class:`~instance.web.search.Facet` descriptor from a
     * filter descriptor
     *
     * @returns {Object}
     */
    facetFor: function () {
        var fieldDescription;
        var timeRange = "[]";
        var timeRangeDescription;
        var comparisonTimeRange = "[]";
        var comparisonTimeRangeDescription;

        if (this.isActive) {
            fieldDescription = this.dateField.description;
            if (this.timeRangeId !== 'custom') {
                timeRange = Domain.prototype.constructDomain(
                    this.dateField.name,
                    this.timeRangeId,
                    this.dateField.type
                );
                timeRangeDescription = _.findWhere(
                    this.periodOptions,
                    {optionId: this.timeRangeId}
                ).description;
            }
            if (this.comparisonIsSelected) {
                comparisonTimeRange = Domain.prototype.constructDomain(
                    this.dateField.name,
                    this.timeRangeId,
                    this.dateField.type,
                    null,
                    this.comparisonTimeRangeId
                );
                comparisonTimeRangeDescription = _.findWhere(
                    this.comparisonOptions,
                    {optionId: this.comparisonTimeRangeId}
                ).description;
            }
        }

        return {
            cat: 'timeRangeCategory',
            category: _t("Time Range"),
            icon: 'fa fa-calendar',
            field: {
                get_context: function (facet, noDomainEvaluation) {
                    if (!noDomainEvaluation) {
                            timeRange = Domain.prototype.stringToArray(timeRange);
                            comparisonTimeRange = Domain.prototype.stringToArray(comparisonTimeRange);
                    }
                    return {
                        timeRangeMenuData: {
                            timeRange: timeRange,
                            timeRangeDescription: timeRangeDescription,
                            comparisonTimeRange: comparisonTimeRange,
                            comparisonTimeRangeDescription: comparisonTimeRangeDescription,
                        }
                    };
                },
                get_groupby: function () {},
                get_domain: function () {}
            },
            isRange: true,
            values: [{
                label: fieldDescription + ': ' + timeRangeDescription +
                    (
                        comparisonTimeRangeDescription ?
                            (' / ' + comparisonTimeRangeDescription) :
                            ''
                    ),
                value: null,
            }],
        };
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onApplyButtonClick: function () {
        this.isActive = true;
        var dateFieldName = this.$('.o_date_field_selector').val();
        this.timeRangeId = this.$('.o_time_range_selector').val();
        if (this.comparisonIsSelected) {
            this.comparisonTimeRangeId = this.$('.o_comparison_time_range_selector').val();
        }
        this.dateField = {
            name: dateFieldName,
            type: _.findWhere(this.dateFields, {name: dateFieldName}).type,
            description: _.findWhere(this.dateFields, {name: dateFieldName}).string,
        };

        this.renderElement();
        this.trigger_up('time_range_modified');
    },
    /**
     * @private
     *
     * @param {JQueryEvent} ev
     */
    _onCheckBoxClick: function (ev) {
        ev.stopPropagation();
        this.comparisonIsSelected = this.$('.o_comparison_checkbox').prop('checked');
        this.$('.o_comparison_time_range_selector').toggleClass('o_hidden');
        this.$el.addClass('open');
    }
});

return TimeRangeMenu;

});
