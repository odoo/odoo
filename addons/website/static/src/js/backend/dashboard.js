odoo.define('website.backend.dashboard', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
const { loadBundle } = require("@web/core/assets");
var core = require('web.core');
var field_utils = require('web.field_utils');
var pyUtils = require('web.py_utils');
var session = require('web.session');
var time = require('web.time');
var web_client = require('web.web_client');

var QWeb = core.qweb;

var COLORS = ["#1f77b4", "#aec7e8"];
var FORMAT_OPTIONS = {
    // allow to decide if utils.human_number should be used
    humanReadable: function (value) {
        return Math.abs(value) >= 1000;
    },
    // with the choices below, 1236 is represented by 1.24k
    minDigits: 1,
    decimals: 2,
    // avoid comma separators for thousands in numbers when human_number is used
    formatterCallback: function (str) {
        return str;
    },
};

var Dashboard = AbstractAction.extend({
    hasControlPanel: true,
    contentTemplate: 'website.WebsiteDashboardMain',
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],
    events: {
        'click .o_dashboard_action': 'on_dashboard_action',
        'click .o_dashboard_action_form': 'on_dashboard_action_form',
    },

    init: function(parent, context) {
        this._super(parent, context);

        this.DATE_FORMAT = time.getLangDateFormat();
        this.date_range = 'week';  // possible values : 'week', 'month', year'
        this.date_from = moment.utc().subtract(1, 'week');
        this.date_to = moment.utc();

        this.dashboards_templates = ['website.dashboard_header', 'website.dashboard_content'];
        this.graphs = [];
        this.chartIds = {};
    },

    willStart: function() {
        var self = this;
        return Promise.all([loadBundle(this), this._super()]).then(function() {
            return self.fetch_data();
        }).then(function(){
            var website = _.findWhere(self.websites, {selected: true});
            self.website_id = website ? website.id : false;
        });
    },

    start: function() {
        var self = this;
        this._computeControlPanelProps();
        return this._super().then(function() {
            self.render_graphs();
        });
    },

    on_attach_callback: function () {
        this._isInDom = true;
        this.render_graphs();
        this._super.apply(this, arguments);
    },
    on_detach_callback: function () {
        this._isInDom = false;
        this._super.apply(this, arguments);
    },
    /**
     * Fetches dashboard data
     */
    fetch_data: function() {
        var self = this;
        var prom = this._rpc({
            route: '/website/fetch_dashboard_data',
            params: {
                website_id: this.website_id || false,
                date_from: this.date_from.year()+'-'+(this.date_from.month()+1)+'-'+this.date_from.date(),
                date_to: this.date_to.year()+'-'+(this.date_to.month()+1)+'-'+this.date_to.date(),
            },
        });
        prom.then(function (result) {
            self.data = result;
            self.dashboards_data = result.dashboards;
            self.currency_id = result.currency_id;
            self.groups = result.groups;
            self.websites = result.websites;
        });
        return prom;
    },

    on_go_to_website: function (ev) {
        ev.preventDefault();
        var website = _.findWhere(this.websites, {selected: true});
        window.location.replace(`/web#action=website.website_preview&website_id=${encodeURIComponent(website.id)}`);
    },


    render_dashboards: function() {
        var self = this;
        _.each(this.dashboards_templates, function(template) {
            self.$('.o_website_dashboard').append(QWeb.render(template, {widget: self}));
        });
    },

    render_graph: function(div_to_display, chart_values, chart_id) {
        var self = this;

        this.$(div_to_display).empty();
        var $canvasContainer = $('<div/>', {class: 'o_graph_canvas_container'});
        this.$canvas = $('<canvas/>').attr('id', chart_id);
        $canvasContainer.append(this.$canvas);
        this.$(div_to_display).append($canvasContainer);

        var labels = chart_values[0].values.map(function (date) {
            return moment(date[0], "YYYY-MM-DD", 'en');
        });

        var datasets = chart_values.map(function (group, index) {
            return {
                label: group.key,
                data: group.values.map(function (value) {
                    return value[1];
                }),
                dates: group.values.map(function (value) {
                    return value[0];
                }),
                fill: false,
                borderColor: COLORS[index],
            };
        });

        var ctx = this.$canvas[0];
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets,
            },
            options: {
                legend: {
                    display: false,
                },
                maintainAspectRatio: false,
                scales: {
                    yAxes: [{
                        type: 'linear',
                        ticks: {
                            beginAtZero: true,
                            callback: this.formatValue.bind(this),
                        },
                    }],
                    xAxes: [{
                        ticks: {
                            callback: function (moment) {
                                return moment.format(self.DATE_FORMAT);
                            },
                        }
                    }],
                },
                tooltips: {
                    mode: 'index',
                    intersect: false,
                    bodyFontColor: 'rgba(0,0,0,1)',
                    titleFontSize: 13,
                    titleFontColor: 'rgba(0,0,0,1)',
                    backgroundColor: 'rgba(255,255,255,0.6)',
                    borderColor: 'rgba(0,0,0,0.2)',
                    borderWidth: 2,
                    callbacks: {
                        title: function (tooltipItems, data) {
                            return data.datasets[0].label;
                        },
                        label: function (tooltipItem, data) {
                            var moment = data.labels[tooltipItem.index];
                            var date = tooltipItem.datasetIndex === 0 ?
                                        moment :
                                        moment.subtract(1, self.date_range);
                            return date.format(self.DATE_FORMAT) + ': ' + self.formatValue(tooltipItem.yLabel);
                        },
                        labelColor: function (tooltipItem, chart) {
                            var dataset = chart.data.datasets[tooltipItem.datasetIndex];
                            return {
                                borderColor: dataset.borderColor,
                                backgroundColor: dataset.borderColor,
                            };
                        },
                    }
                }
            }
        });
    },

    render_graphs: function() {
        var self = this;
        if (this._isInDom) {
            _.each(this.graphs, function(e) {
                var renderGraph = self.groups[e.group] &&
                                    self.dashboards_data[e.name].summary.order_count;
                if (!self.chartIds[e.name]) {
                    self.chartIds[e.name] = _.uniqueId('chart_' + e.name);
                }
                var chart_id = self.chartIds[e.name];
                if (renderGraph) {
                    self.render_graph('.o_graph_' + e.name, self.dashboards_data[e.name].graph, chart_id);
                }
            });
        }
    },

    on_date_range_button: function(date_range) {
        if (date_range === 'week') {
            this.date_range = 'week';
            this.date_from = moment.utc().subtract(1, 'weeks');
        } else if (date_range === 'month') {
            this.date_range = 'month';
            this.date_from = moment.utc().subtract(1, 'months');
        } else if (date_range === 'year') {
            this.date_range = 'year';
            this.date_from = moment.utc().subtract(1, 'years');
        } else {
            console.log('Unknown date range. Choose between [week, month, year]');
            return;
        }

        var self = this;
        Promise.resolve(this.fetch_data()).then(function () {
            self.$('.o_website_dashboard').empty();
            self.render_dashboards();
            self.render_graphs();
        });

    },

    on_website_button: function(website_id) {
        var self = this;
        this.website_id = website_id;
        Promise.resolve(this.fetch_data()).then(function () {
            self.$('.o_website_dashboard').empty();
            self.render_dashboards();
            self.render_graphs();
        });
    },

    on_reverse_breadcrumb: function() {
        var self = this;
        web_client.do_push_state({});
        this.fetch_data().then(function() {
            self.$('.o_website_dashboard').empty();
            self.render_dashboards();
            self.render_graphs();
        });
    },

    on_dashboard_action: function (ev) {
        ev.preventDefault();
        var self = this
        var $action = $(ev.currentTarget);
        var additional_context = {};
        if (this.date_range === 'week') {
            additional_context = {search_default_week: true};
        } else if (this.date_range === 'month') {
            additional_context = {search_default_month: true};
        } else if (this.date_range === 'year') {
            additional_context = {search_default_year: true};
        }
        this._rpc({
            route: '/web/action/load',
            params: {
                'action_id': $action.attr('name'),
            },
        })
        .then(function (action) {
            action.domain = pyUtils.assembleDomains([action.domain, `[('website_id', '=', ${self.website_id})]`]);
            return self.do_action(action, {
                'additional_context': additional_context,
                'on_reverse_breadcrumb': self.on_reverse_breadcrumb
            });
        });
    },

    on_dashboard_action_form: function (ev) {
        ev.preventDefault();
        var $action = $(ev.currentTarget);
        this.do_action({
            name: $action.attr('name'),
            res_model: $action.data('res_model'),
            res_id: $action.data('res_id'),
            views: [[false, 'form']],
            type: 'ir.actions.act_window',
        }, {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb
        });
    },

    /**
     * @private
     */
    _computeControlPanelProps() {
        const $searchview = $(QWeb.render("website.DateRangeButtons", {
            widget: this,
        }));
        $searchview.find('button.js_date_range').click((ev) => {
            $searchview.find('button.js_date_range.active').removeClass('active');
            $(ev.target).addClass('active');
            this.on_date_range_button($(ev.target).data('date'));
        });
        $searchview.find('button.js_website').click((ev) => {
            $searchview.find('button.js_website.active').removeClass('active');
            $(ev.target).addClass('active');
            this.on_website_button($(ev.target).data('website-id'));
        });

        const $buttons = $(QWeb.render("website.GoToButtons"));
        $buttons.on('click', this.on_go_to_website.bind(this));

        this.controlPanelProps.cp_content = { $searchview, $buttons };
    },

    // Utility functions
    getValue: function(d) { return d[1]; },
    format_number: function(value, type, digits, symbol) {
        if (type === 'currency') {
            return this.render_monetary_field(value, this.currency_id);
        } else {
            return field_utils.format[type](value || 0, {digits: digits}) + ' ' + symbol;
        }
    },
    formatValue: function (value) {
        var formatter = field_utils.format.float;
        var formatedValue = formatter(value, undefined, FORMAT_OPTIONS);
        return formatedValue;
    },
    render_monetary_field: function(value, currency_id) {
        var currency = session.get_currency(currency_id);
        var formatted_value = field_utils.format.float(value || 0, {digits: currency && currency.digits});
        if (currency) {
            if (currency.position === "after") {
                formatted_value += currency.symbol;
            } else {
                formatted_value = currency.symbol + formatted_value;
            }
        }
        return formatted_value;
    },

});

core.action_registry.add('backend_dashboard', Dashboard);

return Dashboard;
});
