odoo.define('website_links.charts', function (require) {
'use strict';

var core = require('web.core');
var publicWidget = require('web.public.widget');

var _t = core._t;

var BarChart = publicWidget.Widget.extend({
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],
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
        // Fill data for each day (with 0 click for days without data)
        var clicksArray = [];
        var beginDateCopy = this.beginDate;
        for (var i = 0; i < this.number_of_days; i++) {
            var dateKey = beginDateCopy.format('YYYY-MM-DD');
            clicksArray.push([dateKey, (dateKey in this.dates) ? this.dates[dateKey] : 0]);
            beginDateCopy.add(1, 'days');
        }

        var nbClicks = 0;
        var data = [];
        var labels = [];
        clicksArray.forEach(function (pt) {
            labels.push(pt[0]);
            nbClicks += pt[1];
            data.push(pt[1]);
        });

        this.$('.title').html(nbClicks + _t(' clicks'));

        var config = {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    fill: 'start',
                    label: _t('# of clicks'),
                    backgroundColor: '#ebf2f7',
                    borderColor: '#6aa1ca',

                }],
            },
        };
        var canvas = this.$('canvas')[0];
        var context = canvas.getContext('2d');
        new Chart(context, config);
    },
});

var PieChart = publicWidget.Widget.extend({
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],
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

        // Process country data to fit into the ChartJS scheme
        var labels = [];
        var data = [];
        for (var i = 0; i < this.data.length; i++) {
            var countryName = this.data[i]['country_id'] ? this.data[i]['country_id'][1] : _t('Undefined');
            labels.push(countryName + ' (' + this.data[i]['country_id_count'] + ')');
            data.push(this.data[i]['country_id_count']);
        }

        // Set title
        this.$('.title').html(this.data.length + _t(' countries'));

        var config = {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    label: this.data[0].key,
                }]
            },
        };

        var canvas = this.$('canvas')[0];
        var context = canvas.getContext('2d');
        new Chart(context, config);
    },
});

publicWidget.registry.websiteLinksCharts = publicWidget.Widget.extend({
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

        return Promise.all(defs).then(function (results) {
            var _totalClicks = results[0];
            var _clicksByDay = results[1];
            var _clicksByCountry = results[2];
            var _lastWeekClicksByCountry = results[3];
            var _lastMonthClicksByCountry = results[4];

            if (!_totalClicks) {
                $('#all_time_charts').prepend(_t("There is no data to show"));
                $('#last_month_charts').prepend(_t("There is no data to show"));
                $('#last_week_charts').prepend(_t("There is no data to show"));
                return;
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
            self.charts.all_time_bar = new BarChart(this, beginDate, now, formattedClicksByDay);
            self.charts.all_time_bar.attachTo($('#all_time_clicks_chart'));

            // Process month line chart data
            beginDate = moment().subtract(30, 'days');
            self.charts.last_month_bar = new BarChart(this, beginDate, now, formattedClicksByDay);
            self.charts.last_month_bar.attachTo($('#last_month_clicks_chart'));

            // Process week line chart data
            beginDate = moment().subtract(7, 'days');
            self.charts.last_week_bar = new BarChart(this, beginDate, now, formattedClicksByDay);
            self.charts.last_week_bar.attachTo($('#last_week_clicks_chart'));

            // Process pie charts
            self.charts.all_time_pie = new PieChart(this, _clicksByCountry);
            self.charts.all_time_pie.attachTo($('#all_time_countries_charts'));

            self.charts.last_month_pie = new PieChart(this, _lastMonthClicksByCountry);
            self.charts.last_month_pie.attachTo($('#last_month_countries_charts'));

            self.charts.last_week_pie = new PieChart(this, _lastWeekClicksByCountry);
            self.charts.last_week_pie.attachTo($('#last_week_countries_charts'));

            var rowWidth = $('#all_time_countries_charts').parent().width();
            var $chartCanvas = $('#all_time_countries_charts,last_month_countries_charts,last_week_countries_charts').find('canvas');
            $chartCanvas.height(Math.max(_clicksByCountry.length * (rowWidth > 750 ? 1 : 2), 20) + 'em');

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
     * @private
     * @param {Event} ev
     */
    _onGraphTabClick: function (ev) {
        ev.preventDefault();
        $('.graph-tabs li a').tab('show');
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
