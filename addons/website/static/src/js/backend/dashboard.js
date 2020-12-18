odoo.define('website.backend.dashboard', function (require) {
'use strict';

var AbstractAction = require('web.AbstractAction');
var ajax = require('web.ajax');
var core = require('web.core');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');
var pyUtils = require('web.py_utils');
var session = require('web.session');
var time = require('web.time');
var web_client = require('web.web_client');

var _t = core._t;
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
        'click .js_link_analytics_settings': 'on_link_analytics_settings',
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
        return Promise.all([ajax.loadLibs(this), this._super()]).then(function() {
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

    on_link_analytics_settings: function(ev) {
        ev.preventDefault();

        var self = this;
        var dialog = new Dialog(this, {
            size: 'medium',
            title: _t('Connect Google Analytics'),
            $content: QWeb.render('website.ga_dialog_content', {
                ga_key: this.dashboards_data.visits.ga_client_id,
                ga_analytics_key: this.dashboards_data.visits.ga_analytics_key,
            }),
            buttons: [
                {
                    text: _t("Save"),
                    classes: 'btn-primary',
                    close: true,
                    click: function() {
                        var ga_client_id = dialog.$el.find('input[name="ga_client_id"]').val();
                        var ga_analytics_key = dialog.$el.find('input[name="ga_analytics_key"]').val();
                        self.on_save_ga_client_id(ga_client_id, ga_analytics_key);
                    },
                },
                {
                    text: _t("Cancel"),
                    close: true,
                },
            ],
        }).open();
    },

    on_go_to_website: function (ev) {
        ev.preventDefault();
        var website = _.findWhere(this.websites, {selected: true});
        window.location.href = $.param.querystring(website.domain + '/', {'fw': website.id});
    },

    on_save_ga_client_id: function(ga_client_id, ga_analytics_key) {
        var self = this;
        return this._rpc({
            route: '/website/dashboard/set_ga_data',
            params: {
                'website_id': self.website_id,
                'ga_client_id': ga_client_id,
                'ga_analytics_key': ga_analytics_key,
            },
        }).then(function (result) {
            if (result.error) {
                self.do_warn(result.error.title, result.error.message);
                return;
            }
            self.on_date_range_button('week');
        });
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
            this.render_graph_analytics(this.dashboards_data.visits.ga_client_id);
        }
    },

    render_graph_analytics: function(client_id) {
        if (!this.dashboards_data.visits || !this.dashboards_data.visits.ga_client_id) {
          return;
        }

        this.load_analytics_api();

        var $analytics_components = this.$('.js_analytics_components');
        this.addLoader($analytics_components);

        var self = this;
        gapi.analytics.ready(function() {

            $analytics_components.empty();
            // 1. Authorize component
            var $analytics_auth = $('<div>').addClass('col-lg-12');
            window.onOriginError = function () {
                $analytics_components.find('.js_unauthorized_message').remove();
                self.display_unauthorized_message($analytics_components, 'not_initialized');
            };
            gapi.analytics.auth.authorize({
                container: $analytics_auth[0],
                clientid: client_id
            });

            $analytics_auth.appendTo($analytics_components);

            self.handle_analytics_auth($analytics_components);
            gapi.analytics.auth.on('signIn', function() {
                delete window.onOriginError;
                self.handle_analytics_auth($analytics_components);
            });

        });
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

    // Loads Analytics API
    load_analytics_api: function() {
        var self = this;
        if (!("gapi" in window)) {
            (function(w,d,s,g,js,fjs){
                g=w.gapi||(w.gapi={});g.analytics={q:[],ready:function(cb){this.q.push(cb);}};
                js=d.createElement(s);fjs=d.getElementsByTagName(s)[0];
                js.src='https://apis.google.com/js/platform.js';
                fjs.parentNode.insertBefore(js,fjs);js.onload=function(){g.load('analytics');};
            }(window,document,'script'));
            gapi.analytics.ready(function() {
                self.analytics_create_components();
            });
        }
    },

    handle_analytics_auth: function($analytics_components) {
        $analytics_components.find('.js_unauthorized_message').remove();

        // Check if the user is authenticated and has the right to make API calls
        if (!gapi.analytics.auth.getAuthResponse()) {
            this.display_unauthorized_message($analytics_components, 'not_connected');
        } else if (gapi.analytics.auth.getAuthResponse() && gapi.analytics.auth.getAuthResponse().scope.indexOf('https://www.googleapis.com/auth/analytics') === -1) {
            this.display_unauthorized_message($analytics_components, 'no_right');
        } else {
            this.make_analytics_calls($analytics_components);
        }
    },

    display_unauthorized_message: function($analytics_components, reason) {
        $analytics_components.prepend($(QWeb.render('website.unauthorized_analytics', {reason: reason})));
    },

    make_analytics_calls: function($analytics_components) {
        // 2. ActiveUsers component
        var $analytics_users = $('<div>');
        var activeUsers = new gapi.analytics.ext.ActiveUsers({
            container: $analytics_users[0],
            pollingInterval: 10,
        });
        $analytics_users.appendTo($analytics_components);

        // 3. View Selector
        var $analytics_view_selector = $('<div>').addClass('col-lg-12 o_properties_selection');
        var viewSelector = new gapi.analytics.ViewSelector({
            container: $analytics_view_selector[0],
        });
        viewSelector.execute();
        $analytics_view_selector.appendTo($analytics_components);

        // 4. Chart graph
        var start_date = '7daysAgo';
        if (this.date_range === 'month') {
            start_date = '30daysAgo';
        } else if (this.date_range === 'year') {
            start_date = '365daysAgo';
        }
        var $analytics_chart_2 = $('<div>').addClass('col-lg-6 col-12');
        var breakdownChart = new gapi.analytics.googleCharts.DataChart({
            query: {
                'dimensions': 'ga:date',
                'metrics': 'ga:sessions',
                'start-date': start_date,
                'end-date': 'yesterday'
            },
            chart: {
                type: 'LINE',
                container: $analytics_chart_2[0],
                options: {
                    title: 'All',
                    width: '100%',
                    tooltip: {isHtml: true},
                }
            }
        });
        $analytics_chart_2.appendTo($analytics_components);

        // 5. Chart table
        var $analytics_chart_1 = $('<div>').addClass('col-lg-6 col-12');
        var mainChart = new gapi.analytics.googleCharts.DataChart({
            query: {
                'dimensions': 'ga:medium',
                'metrics': 'ga:sessions',
                'sort': '-ga:sessions',
                'max-results': '6'
            },
            chart: {
                type: 'TABLE',
                container: $analytics_chart_1[0],
                options: {
                    width: '100%'
                }
            }
        });
        $analytics_chart_1.appendTo($analytics_components);

        // Events handling & animations

        var table_row_listener;

        viewSelector.on('change', function(ids) {
            var options = {query: {ids: ids}};
            activeUsers.set({ids: ids}).execute();
            mainChart.set(options).execute();
            breakdownChart.set(options).execute();

            if (table_row_listener) { google.visualization.events.removeListener(table_row_listener); }
        });

        mainChart.on('success', function(response) {
            var chart = response.chart;
            var dataTable = response.dataTable;

            table_row_listener = google.visualization.events.addListener(chart, 'select', function() {
                var options;
                if (chart.getSelection().length) {
                    var row =  chart.getSelection()[0].row;
                    var medium =  dataTable.getValue(row, 0);
                    options = {
                        query: {
                            filters: 'ga:medium==' + medium,
                        },
                        chart: {
                            options: {
                                title: medium,
                            }
                        }
                    };
                } else {
                    options = {
                        chart: {
                            options: {
                                title: 'All',
                            }
                        }
                    };
                    delete breakdownChart.get().query.filters;
                }
                breakdownChart.set(options).execute();
            });
        });

        // Add CSS animation to visually show the when users come and go.
        activeUsers.once('success', function() {
            var element = this.container.firstChild;
            var timeout;

            this.on('change', function(data) {
                element = this.container.firstChild;
                var animationClass = data.delta > 0 ? 'is-increasing' : 'is-decreasing';
                element.className += (' ' + animationClass);

                clearTimeout(timeout);
                timeout = setTimeout(function() {
                    element.className = element.className.replace(/ is-(increasing|decreasing)/g, '');
                }, 3000);
            });
        });
    },

    /*
     * Credits to https://github.com/googleanalytics/ga-dev-tools
     * This is the Active Users component that polls
     * the number of active users on Analytics each 5 secs
     */
    analytics_create_components: function() {

        gapi.analytics.createComponent('ActiveUsers', {

            initialize: function() {
                this.activeUsers = 0;
                gapi.analytics.auth.once('signOut', this.handleSignOut_.bind(this));
            },

            execute: function() {
                // Stop any polling currently going on.
                if (this.polling_) {
                    this.stop();
                }

                this.render_();

                // Wait until the user is authorized.
                if (gapi.analytics.auth.isAuthorized()) {
                    this.pollActiveUsers_();
                } else {
                    gapi.analytics.auth.once('signIn', this.pollActiveUsers_.bind(this));
                }
            },

            stop: function() {
                clearTimeout(this.timeout_);
                this.polling_ = false;
                this.emit('stop', {activeUsers: this.activeUsers});
            },

            render_: function() {
                var opts = this.get();

                // Render the component inside the container.
                this.container = typeof opts.container === 'string' ?
                    document.getElementById(opts.container) : opts.container;

                this.container.innerHTML = opts.template || this.template;
                this.container.querySelector('b').innerHTML = this.activeUsers;
            },

            pollActiveUsers_: function() {
                var options = this.get();
                var pollingInterval = (options.pollingInterval || 5) * 1000;

                if (isNaN(pollingInterval) || pollingInterval < 5000) {
                    throw new Error('Frequency must be 5 seconds or more.');
                }

                this.polling_ = true;
                gapi.client.analytics.data.realtime
                    .get({ids:options.ids, metrics:'rt:activeUsers'})
                    .then(function(response) {
                        var result = response.result;
                        var newValue = result.totalResults ? +result.rows[0][0] : 0;
                        var oldValue = this.activeUsers;

                        this.emit('success', {activeUsers: this.activeUsers});

                        if (newValue !== oldValue) {
                            this.activeUsers = newValue;
                            this.onChange_(newValue - oldValue);
                        }

                        if (this.polling_) {
                            this.timeout_ = setTimeout(this.pollActiveUsers_.bind(this), pollingInterval);
                        }
                    }.bind(this));
            },

            onChange_: function(delta) {
                var valueContainer = this.container.querySelector('b');
                if (valueContainer) { valueContainer.innerHTML = this.activeUsers; }

                this.emit('change', {activeUsers: this.activeUsers, delta: delta});
                if (delta > 0) {
                    this.emit('increase', {activeUsers: this.activeUsers, delta: delta});
                } else {
                    this.emit('decrease', {activeUsers: this.activeUsers, delta: delta});
                }
            },

            handleSignOut_: function() {
                this.stop();
                gapi.analytics.auth.once('signIn', this.handleSignIn_.bind(this));
            },

            handleSignIn_: function() {
                this.pollActiveUsers_();
                gapi.analytics.auth.once('signOut', this.handleSignOut_.bind(this));
            },

            template:
                '<div class="ActiveUsers">' +
                    'Active Users: <b class="ActiveUsers-value"></b>' +
                '</div>'

        });
    },

    // Utility functions
    addLoader: function(selector) {
        var loader = '<span class="fa fa-3x fa-spin fa-spinner fa-pulse"/>';
        selector.html("<div class='o_loader'>" + loader + "</div>");
    },
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
