/** @odoo-module **/

import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { browser } from "@web/core/browser/browser";
const { DateTime } = luxon;

var BarChart = publicWidget.Widget.extend({
    /**
     * @constructor
     * @param {Object} parent
     * @param {Object} beginDate
     * @param {Object} endDate
     * @param {Object} dates
     */
    init: function (parent, beginDate, endDate, dates) {
        this._super.apply(this, arguments);
        this.beginDate = beginDate.startOf("day");
        this.endDate = endDate.startOf("day");
        if (this.beginDate.toISO() === this.endDate.toISO()) {
            this.endDate = this.endDate.plus({ days: 1 });
        }
        this.number_of_days = this.endDate.diff(this.beginDate).as("days");
        this.dates = dates;
    },
    /**
     * @override
     */
    start: function () {
        // Fill data for each day (with 0 click for days without data)
        var clicksArray = [];
        for (var i = 0; i <= this.number_of_days; i++) {
            var dateKey = this.beginDate.toFormat("yyyy-MM-dd");
            clicksArray.push([dateKey, (dateKey in this.dates) ? this.dates[dateKey] : 0]);
            this.beginDate = this.beginDate.plus({ days: 1 });
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
    willStart: async function () {
        await loadBundle("web.chartjs_lib");
    },
});

var PieChart = publicWidget.Widget.extend({
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
                    label: this.data.length > 0 ? this.data[0].key : _t('No data'),
                }]
            },
            options: {
                aspectRatio: 2,
            },
        };

        var canvas = this.$('canvas')[0];
        var context = canvas.getContext('2d');
        new Chart(context, config);
    },
    willStart: async function () {
        await loadBundle("web.chartjs_lib");
    },
});

publicWidget.registry.websiteLinksCharts = publicWidget.Widget.extend({
    selector: '.o_website_links_chart',
    events: {
        'click .copy-to-clipboard': '_onCopyToClipboardClick',
    },

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * @override
     */
    start: async function () {
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
                // This is a trick to get the date without the local formatting.
                // We can't simply do .locale("en") because some Odoo languages
                // are not supported by moment.js (eg: Arabic Syria).
                // FIXME this now uses luxon, check if this is still needed? Probably can be replaced by deserializeDate
                const date = DateTime.fromFormat(
                    _clicksByDay[i]["__domain"].find((el) => el.length && el.includes(">="))[2]
                        .split(" ")[0], "yyyy-MM-dd"
                );
                if (i === 0) {
                    beginDate = date;
                }
                formattedClicksByDay[date.setLocale("en").toFormat("yyyy-MM-dd")] =
                    _clicksByDay[i]["create_date_count"];
            }

            // Process all time line chart data
            var now = DateTime.now();
            self.charts.all_time_bar = new BarChart(self, beginDate, now, formattedClicksByDay);
            self.charts.all_time_bar.attachTo($('#all_time_clicks_chart'));

            // Process month line chart data
            beginDate = DateTime.now().minus({ days: 30 });
            self.charts.last_month_bar = new BarChart(self, beginDate, now, formattedClicksByDay);
            self.charts.last_month_bar.attachTo($('#last_month_clicks_chart'));

            // Process week line chart data
            beginDate = DateTime.now().minus({ days: 7 });
            self.charts.last_week_bar = new BarChart(self, beginDate, now, formattedClicksByDay);
            self.charts.last_week_bar.attachTo($('#last_week_clicks_chart'));

            // Process pie charts
            self.charts.all_time_pie = new PieChart(self, _clicksByCountry);
            self.charts.all_time_pie.attachTo($('#all_time_countries_charts'));

            self.charts.last_month_pie = new PieChart(self, _lastMonthClicksByCountry);
            self.charts.last_month_pie.attachTo($('#last_month_countries_charts'));

            self.charts.last_week_pie = new PieChart(self, _lastWeekClicksByCountry);
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
        return this.orm.searchCount("link.tracker.click", [this.links_domain]);
    },
    /**
     * @private
     */
    _clicksByDay: function () {
        return this.orm.readGroup(
            "link.tracker.click",
            [this.links_domain],
            ["create_date"],
            ["create_date:day"]
        );
    },
    /**
     * @private
     */
    _clicksByCountry: function () {
        return this.orm.readGroup(
            "link.tracker.click",
            [this.links_domain],
            ["country_id"],
            ["country_id"]
        );
    },
    /**
     * @private
     */
    _lastWeekClicksByCountry: function () {
        // 7 days * 24 hours * 60 minutes * 60 seconds * 1000 milliseconds.
        const aWeekAgoDate = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
        // get the date in the format YYYY-MM-DD.
        const aWeekAgoString = aWeekAgoDate.toISOString().split("T")[0];
        return this.orm.readGroup(
            "link.tracker.click",
            [this.links_domain, ["create_date", ">", aWeekAgoString]],
            ["country_id"],
            ["country_id"]
        );
    },
    /**
     * @private
     */
    _lastMonthClicksByCountry: function () {
        // 30 days * 24 hours * 60 minutes * 60 seconds * 1000 milliseconds.
        const aMonthAgoDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        // get the date in the format YYYY-MM-DD.
        const aMonthAgoString = aMonthAgoDate.toISOString().split("T")[0];
        return this.orm.readGroup(
            "link.tracker.click",
            [this.links_domain, ["create_date", ">", aMonthAgoString]],
            ["country_id"],
            ["country_id"]
        );
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onCopyToClipboardClick: async function (ev) {
        ev.preventDefault();

        const textValue = ev.target.dataset["clipboard-text"];
        await browser.navigator.clipboard.writeText(textValue);

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

export default {
    BarChart: BarChart,
    PieChart: PieChart,
};
