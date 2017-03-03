odoo.define('website.backendDashboard', function (require) {
"use strict";


var ajax = require('web.ajax');
var ControlPanelMixin = require('web.ControlPanelMixin');
var core = require('web.core');
var Dialog = require('web.Dialog');
var formats = require('web.formats');
var Model = require('web.Model');
var session = require('web.session');
var web_client = require('web.web_client');
var Widget = require('web.Widget');

var local_storage = require('web.local_storage');

var _t = core._t;
var QWeb = core.qweb;

var Dashboard = Widget.extend(ControlPanelMixin, {
    template: "website.WebsiteDashboardMain",
    events: {
        'click .js_link_analytics_settings': 'on_link_analytics_settings',
        'click .o_dashboard_action': 'on_dashboard_action',
        'click .o_dashboard_action_form': 'on_dashboard_action_form',
        'click .o_dashboard_hide_panel': 'on_dashboard_hide_panel',
    },

    init: function(parent, context) {
        this._super(parent, context);

        this.date_range = 'week';  // possible values : 'week', 'month', year'
        this.date_from = moment().subtract(1, 'week');
        this.date_to = moment();
        this.hidden_apps = JSON.parse(local_storage.getItem('website_dashboard_hidden_app_ids') || '[]');

        this.dashboards_templates = ['website.dashboard_visits'];
        this.graphs = [];
    },

    willStart: function() {
        var self = this;
        return this._super().then(function() {
            return $.when(
                self.fetch_data()
            );
        });
    },

    start: function() {
        var self = this;
        return this._super().then(function() {
            self.update_cp();
            self.render_dashboards();
            self.render_graphs();
            self.$el.parent().addClass('oe_background_grey');
        });
    },

    fetch_data: function() {
        var self = this;
        return ajax.jsonRpc('/website/fetch_dashboard_data', 'call', {
            'date_from': this.date_from.format('YYYY-MM-DD'),
            'date_to': this.date_to.format('YYYY-MM-DD'),
        }).done(function(result) {
            self.data = result;
            self.dashboards_data = result.dashboards;
            self.currency_id = result.currency_id;
            self.groups = result.groups;
        });
    },

    on_link_analytics_settings: function(ev) {
        ev.preventDefault();

        var self = this;
        var dialog = new Dialog(this, {
            size: 'medium',
            title: _t('Google Analytics'),
            $content: QWeb.render('website.ga_dialog_content', {ga_key: this.dashboards_data.visits.ga_client_id}),
            buttons: [
                {
                    text: _t("Save"),
                    classes: 'btn-primary',
                    close: true,
                    click: function() {
                        var ga_client_id = dialog.$el.find('input[name="ga_client_id"]').val();
                        self.on_save_ga_client_id(ga_client_id);
                    },
                },
                {
                    text: _t("Cancel"),
                    close: true,
                },
            ],
        }).open();
    },

    on_save_ga_client_id: function(ga_client_id) {

        if (!ga_client_id.endsWith(".apps.googleusercontent.com") || ga_client_id.startsWith(" ")) {
            this.do_warn(_t('Incorrect Client ID'), _t('The Google Analytics Client ID you have entered seems incorrect.'));
            return;
        }

        var self = this;
        new Model('ir.config_parameter').call('set_param', ['google_management_client_id', ga_client_id]).then(function(){
            self.on_date_range_button('week');
        });
    },

    render_dashboards: function() {
        var self = this;
        _.each(this.dashboards_templates, function(template) {
            self.$('.o_website_dashboard_content').append(QWeb.render(template, {widget: self}));
        });
    },

    render_graph: function(div_to_display, chart_values) {
        this.$(div_to_display).empty();

        var self = this;
        nv.addGraph(function() {
            var chart = nv.models.lineChart()
                .x(function(d) { return self.getDate(d); })
                .y(function(d) { return self.getValue(d); })
                .forceY([0]);
            chart
                .useInteractiveGuideline(true)
                .showLegend(false)
                .showYAxis(true)
                .showXAxis(true);

            var tick_values = self.getPrunedTickValues(chart_values[0].values, 5);

            chart.xAxis
                .tickFormat(function(d) { return d3.time.format("%m/%d/%y")(new Date(d)); })
                .tickValues(_.map(tick_values, function(d) { return self.getDate(d); }))
                .rotateLabels(-45);

            chart.yAxis
                .tickFormat(d3.format('.02f'));

            var svg = d3.select(div_to_display)
                .append("svg");

            svg
                .attr("height", '24em')
                .datum(chart_values)
                .call(chart);

            nv.utils.windowResize(chart.update);
            return chart;
        });
    },

    render_graphs: function() {
        var self = this;
        _.each(this.graphs, function(e) {
            if (self.groups[e.group]) {
                self.render_graph('#o_graph_' + e.name, self.dashboards_data[e.name].graph);
            }
        });
        this.render_graph_analytics(this.dashboards_data.visits.ga_client_id);
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
            var $analytics_auth = $('<div>').addClass('col-md-12');
            gapi.analytics.auth.authorize({
                container: $analytics_auth[0],
                clientid: client_id
            });
            $analytics_auth.appendTo($analytics_components);

            self.handle_analytics_auth($analytics_components);
            gapi.analytics.auth.on('signIn', function() {
                self.handle_analytics_auth($analytics_components);
            });

        });
    },

    on_date_range_button: function(date_range) {
        if (date_range === 'week') {
            this.date_range = 'week';
            this.date_from = moment().subtract(1, 'weeks');
        } else if (date_range === 'month') {
            this.date_range = 'month';
            this.date_from = moment().subtract(1, 'months');
        } else if (date_range === 'year') {
            this.date_range = 'year';
            this.date_from = moment().subtract(1, 'years');
        } else {
            console.log('Unknown date range. Choose between [week, month, year]');
            return;
        }

        var self = this;
        $.when(this.fetch_data()).then(function() {
            self.$('.o_website_dashboard_content').empty();
            self.render_dashboards();
            self.render_graphs();
        });

    },

    on_reverse_breadcrumb: function() {
        web_client.do_push_state({});
        this.update_cp();
    },

    on_dashboard_action: function (ev) {
        ev.preventDefault();
        var $action = $(ev.currentTarget);
        var additional_context = {};
        if (this.date_range === 'week') {
            additional_context = {'search_default_week': true}
        } else if (this.date_range === 'month') {
            additional_context = {'search_default_month': true}
        } else if (this.date_range === 'year') {
            additional_context = {'search_default_year': true}
        }
        this.do_action($action.attr('name'), {
            additional_context: additional_context,
            on_reverse_breadcrumb: this.on_reverse_breadcrumb
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

    on_dashboard_hide_panel: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var $action = $(ev.currentTarget);
        // update hidden module list
        this.hidden_apps = JSON.parse(local_storage.getItem('website_dashboard_hidden_app_ids') || '[]');
        this.hidden_apps.push(JSON.parse($action.data('module_id')));
        local_storage.setItem('website_dashboard_hidden_app_ids', JSON.stringify(this.hidden_apps));
        // remove box
        $action.closest(".o_box_item").remove();
    },

    update_cp: function() {
        var self = this;
        if (!this.$searchview) {
            this.$searchview = $(QWeb.render("website.DateRangeButtons", {
                widget: this,
            }));
            this.$searchview.click('button.js_date_range', function(ev) {
                self.on_date_range_button($(ev.target).data('date'));
                $(this).find('button.js_date_range.active').removeClass('active');
                $(ev.target).addClass('active');
            });
        }
        this.update_control_panel({
            cp_content: {
                $searchview: this.$searchview,
            },
            breadcrumbs: this.getParent().get_breadcrumbs(),
        });
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
        var $analytics_view_selector = $('<div>').addClass('col-md-12 o_properties_selection');
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
        var $analytics_chart_2 = $('<div>').addClass('col-md-6 col-xs-12');
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
                    width: '100%'
                }
            }
        });
        $analytics_chart_2.appendTo($analytics_components);

        // 5. Chart table
        var $analytics_chart_1 = $('<div>').addClass('col-md-6 col-xs-12');
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
    getDate: function(d) { return new Date(d[0]); },
    getValue: function(d) { return d[1]; },
    getPrunedTickValues: function(ticks, nb_desired_ticks) {
        var nb_values = ticks.length;
        var keep_one_of = Math.max(1, Math.floor(nb_values / nb_desired_ticks));

        return _.filter(ticks, function(d, i) {
            return i % keep_one_of === 0;
        });
    },
    format_number: function(value, type, digits, symbol) {
        if (type === 'currency') {
            return this.render_monetary_field(value, this.currency_id);
        } else {
            return formats.format_value(value || 0, {type: type, digits: digits}) + ' ' + symbol;
        }
    },
    render_monetary_field: function(value, currency_id) {
        var currency = session.get_currency(currency_id);
        var formatted_value = formats.format_value(value || 0, {type: "float", digits: currency && currency.digits});
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
