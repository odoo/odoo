odoo.define('website_links.charts', function (require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');
var sAnimations = require('website.content.snippets.animation');

var _t = core._t;

var BarChart = Widget.extend({
    /**
     * @constructor
     * @param {Object} parent
     * @param {Object} beginDate
     * @param {Object} endDate
     * @param {Object} dates
     */
    init: function (parent, beginDate, endDate, dates) {
        this._super.apply(this, arguments);
        this.beginDate = beginDate;
        this.endDate = endDate;
        this.number_of_days = this.endDate.diff(this.beginDate, 'days') + 2;
        this.dates = dates;
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        // Accessor functions
        function getDate(d) {
            return new Date(d[0]);
        }
        function getNbClicks(d) {
            return d[1];
        }

        // Prune tick values for visibility purpose
        function getPrunedTickValues(ticks, nbDesiredTicks) {
            var nbValues = ticks.length;
            var keepOneOf = Math.max(1, Math.floor(nbValues / nbDesiredTicks));

            return _.filter(ticks, function (d, i) {
                return i % keepOneOf === 0;
            });
        }

        // Fill data for each day (with 0 click for days without data)
        var clicksArray = [];
        var beginDateCopy = this.beginDate;
        for (var i = 0; i < this.number_of_days; i++) {
            var dateKey = beginDateCopy.format('YYYY-MM-DD');
            clicksArray.push([dateKey, (dateKey in this.dates) ? this.dates[dateKey] : 0]);
            beginDateCopy.add(1, 'days');
        }

        // Set title
        var nbClicks = _.reduce(clicksArray, function (total, val) {
            return total + val[1];
        }, 0);
        this.$('.title').html(nbClicks + _t(' clicks'));

        // Fit data into the NVD3 scheme
        var chartData = [{}];
        chartData[0]['key'] = _t('# of clicks');
        chartData[0]['values'] = clicksArray;

        nv.addGraph(function () {
            var chart = nv.models.lineChart()
                .x(function (d) {
                    return getDate(d);
                })
                .y(function (d) {
                    return getNbClicks(d);
                })
                .showYAxis(true)
                .showXAxis(true);

            // Reduce the number of labels on the X axis for visibility
            var tickValues = getPrunedTickValues(chartData[0]['values'], 10);

            chart.xAxis
                .tickFormat(function (d) {
                    return d3.time.format('%d/%m/%y')(new Date(d));
                })
                .tickValues(_.map(tickValues, function (d) {
                    return getDate(d).getTime();
                }))
                .rotateLabels(55);

            chart.yAxis
                .tickFormat(d3.format('d'))
                .ticks(chartData[0]['values'].length - 1);

            d3.select(self.$('svg')[0])
                .datum(chartData)
                .call(chart);

            return self.chart = chart;
        });
    },
});

var PieChart = Widget.extend({
    /**
     * @override
     * @param {Object} parent
     * @param {Object} data
     */
    init: function (parent, data) {
        this._super.apply(this, arguments);
        this.data = data;
    },
    /**
     * @override
     */
    start: function () {
        var self = this;

        // Process country data to fit into the NVD3 scheme
        var processedData = [];
        for (var i = 0; i < this.data.length; i++) {
            var countryName = this.data[i]['country_id'] ? this.data[i]['country_id'][1] : _t('Undefined');
            processedData.push({'label': countryName + ' (' + this.data[i]['country_id_count'] + ')', 'value': this.data[i]['country_id_count']});
        }

        // Set title
        this.$('.title').html(this.data.length + _t(' countries'));

        nv.addGraph(function () {
            var chart = nv.models.pieChart()
                .x(function (d) {
                    return d.label;
                })
                .y(function (d) {
                    return d.value;
                })
                .showLabels(false);

            d3.select(self.$('svg')[0])
                .datum(processedData)
                .transition().duration(1200)
                .call(chart);

            return self.chart = chart;
        });
    },
});

sAnimations.registry.websiteLinksCharts = sAnimations.Class.extend({
    selector: '.o_website_links_chart',
    events: {
        'click .graph-tabs li a': '_onGraphTabClick',
        'click .copy-to-clipboard': '_onCopyToClipboardClick',
    },

    /**
     * @override
     */
    start: function () {
        var self = this;
        this.charts = {};

        // Get the code of the link
        var linkID = parseInt($('#link_id').val());
        this.links_domain = ['link_id', '=', linkID];

        var defs = [];
        defs.push(this._totalClicks());
        defs.push(this._clicksByDay());
        defs.push(this._clicksByCountry());
        defs.push(this._lastWeekClicksByCountry());
        defs.push(this._lastMonthClicksByCountry());
        defs.push(this._super.apply(this, arguments));

        new ClipboardJS($('.copy-to-clipboard')[0]);

        this.animating_copy = false;

        return $.when.apply($, defs).then(function (_totalClicks, _clicksByDay, _clicksByCountry, _lastWeekClicksByCountry, _lastMonthClicksByCountry) {
            if (!_totalClicks) {
                $('#all_time_charts').prepend(_t("There is no data to show"));
                $('#last_month_charts').prepend(_t("There is no data to show"));
                $('#last_week_charts').prepend(_t("There is no data to show"));
            }

            var formattedClicksByDay = {};
            var beginDate;
            for (var i = 0; i < _clicksByDay.length; i++) {
                var date = moment(_clicksByDay[i]['create_date:day'], 'DD MMMM YYYY');
                if (i === 0) {
                    beginDate = date;
                }
                formattedClicksByDay[date.format('YYYY-MM-DD')] = _clicksByDay[i]['create_date_count'];
            }

            // Process all time line chart data
            var now = moment();
            self.charts.all_time_bar = new BarChart(beginDate, now, formattedClicksByDay);
            self.charts.all_time_bar.attachTo($('#all_time_clicks_chart'));

            // Process month line chart data
            beginDate = moment().subtract(30, 'days');
            self.charts.last_month_bar = new BarChart(beginDate, now, formattedClicksByDay);
            self.charts.last_month_bar.attachTo($('#last_month_clicks_chart'));

            // Process week line chart data
            beginDate = moment().subtract(7, 'days');
            self.charts.last_week_bar = new BarChart(beginDate, now, formattedClicksByDay);
            self.charts.last_week_bar.attachTo($('#last_week_clicks_chart'));

            // Process pie charts
            self.charts.all_time_pie = new PieChart(_clicksByCountry);
            self.charts.all_time_pie.attachTo($('#all_time_countries_charts'));

            self.charts.last_month_pie = new PieChart(_lastMonthClicksByCountry);
            self.charts.last_month_pie.attachTo($('#last_month_countries_charts'));

            self.charts.last_week_pie = new PieChart(_lastWeekClicksByCountry);
            self.charts.last_week_pie.attachTo($('#last_week_countries_charts'));

            var rowWidth = $('#all_time_countries_charts').parent().width();
            var chartsSVG = $('#all_time_countries_charts,last_month_countries_charts,last_week_countries_charts').find('svg');
            chartsSVG.css('height', Math.max(_clicksByCountry.length * (rowWidth > 750 ? 1 : 2), 20) + 'em');

            nv.utils.windowResize(function () {
                _.chain(self.charts).pluck('chart').invoke('update');
            });
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _totalClicks: function () {
        return this._rpc({
            model: 'link.tracker.click',
            method: 'search_count',
            args: [[this.links_domain]],
        });
    },
    /**
     * @private
     */
    _clicksByDay: function () {
        return this._rpc({
            model: 'link.tracker.click',
            method: 'read_group',
            args: [[this.links_domain], ['create_date']],
            kwargs: {groupby: 'create_date:day'},
        });
    },
    /**
     * @private
     */
    _clicksByCountry: function () {
        return this._rpc({
            model: 'link.tracker.click',
            method: 'read_group',
            args: [[this.links_domain], ['country_id']],
            kwargs: {groupby: 'country_id'},
        });
    },
    /**
     * @private
     */
    _lastWeekClicksByCountry: function () {
        var interval = moment().subtract(7, 'days').format('YYYY-MM-DD');
        return this._rpc({
            model: 'link.tracker.click',
            method: 'read_group',
            args: [[this.links_domain, ['create_date', '>', interval]], ['country_id']],
            kwargs: {groupby: 'country_id'},
        });
    },
    /**
     * @private
     */
    _lastMonthClicksByCountry: function () {
        var interval = moment().subtract(30, 'days').format('YYYY-MM-DD');
        return this._rpc({
            model: 'link.tracker.click',
            method: 'read_group',
            args: [[this.links_domain, ['create_date', '>', interval]], ['country_id']],
            kwargs: {groupby: 'country_id'},
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Resizes the chart when a tab is opened, because NVD3 automatically reduce
     * the size of the chart to 5px width when the bootstrap tab is closed.
     *
     * @private
     * @param {Event} ev
     */
    _onGraphTabClick: function (ev) {
        ev.preventDefault();
        $('.graph-tabs li a').tab('show');
        _.chain(this.charts).pluck('chart').invoke('update'); // Force NVD3 to redraw the chart
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onCopyToClipboardClick: function (ev) {
        ev.preventDefault();

        if (this.animating_copy) {
            return;
        }

        this.animating_copy = true;

        $('.o_website_links_short_url').clone()
            .css('position', 'absolute')
            .css('left', '15px')
            .css('bottom', '10px')
            .css('z-index', 2)
            .removeClass('.o_website_links_short_url')
            .addClass('animated-link')
            .appendTo($('.o_website_links_short_url'))
            .animate({
                opacity: 0,
                bottom: '+=20',
            }, 500, function () {
                $('.animated-link').remove();
                this.animating_copy = false;
            });
    },
});

return {
    BarChart: BarChart,
    PieChart: PieChart,
};
});
