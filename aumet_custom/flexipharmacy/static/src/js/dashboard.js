odoo.define('aspl_pos_backend_dashboard.dashboard', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var Widget = require('web.Widget');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var session = require('web.session');
    var _t = core._t;

    var POSDashboard = AbstractAction.extend({
        hasControlPanel: true,
        contentTemplate: 'SalesDashboard',

        init: function (parent, params) {
            this._super.apply(this, arguments);
            var self = this;
            this.action_manager = parent;
            this.allowed_company_ids = params.context.allowed_company_ids;
            this.params = params;
            this.company_id = false;
            this.startDate = false;
            this.endDate = false;
            this.currency = false;
            this.currency_id = false;
        },
        set_currency : function(){
            this.currency = session.currencies;
        },
        get_currency : function(id){
             return this.currency[id];
        },
        format_currency: function(amount) {
            var currency = this.get_currency(this.currency_id);
            return currency.position === 'after' ? amount + ' ' + (currency.symbol || ''): (currency.symbol || '') + ' ' + amount;
                return amount + ' ' + (currency.symbol || '');
        },

        events: {
            'change .product-option': 'get_top_product_category',
            'change .product-order': 'get_top_product_category',
            'click .dmy': 'filter_by_d_m_y',
            'change .top-product':'onchange_product_option',
            'change .month-option':'onchange_month_option',
            'change .week-option':'onchange_week_option',
            'change .journal-option':'on_change_journal',
            'change .pos-company': 'filter_dashboard_by_company',
            'change .top_items_sales_w_m_y': 'top_items_by_sales',
            'change .top_product_catg_w_m_y': 'get_top_product_category',
            'change .top_customer_w_m_y': 'get_top_customer',
            'change .top_salesman_w_m_y': 'sales_per_salesperson',
        },

        start: function () {
            this._super.apply(this, arguments);
            this.set("title", this.title);
        },

        willStart:function(){
            var self = this;
            var res = this._super.apply(this, arguments);
            this.company_id = session.user_companies.current_company;
            this.user_companies = session.user_companies.allowed_companies;
            this.set_currency();
            this._rpc({
                model: 'res.company',
                method: 'search_read',
                args: [[['id', '=', this.company_id[0]]], ['currency_id']],
            }, {async: false}).then(function (result) {
                if(result)
                    self.currency_id = result[0].currency_id[0];
            });
            return res;
        },

        filter_dashboard_by_company : function(e){
            var self = this;
            var company_id = self.$el.find(".pos-company option:selected").attr('data-id')
            self.header_data(company_id)
            self.filter_by_d_m_y('', company_id);
            self.payment_by_journal_pie_chart_data(company_id)
            self.sales_per_salesperson(company_id);
            self.customer_avg_visit(company_id);
            self.top_items_by_sales(company_id);
            self.get_top_customer(company_id)
            self.get_top_product_category(company_id);
            self.on_change_journal(company_id);
            self.onchange_week_option(company_id, '');
            self.employee_work_hour(company_id)
            self.daily_gross_sales(company_id);
            self.avg_selling_price(company_id)
            self.weekly_gross_salse(company_id);
        },

        prepare_pie_chart : function(chart_id, pie_data, value_field, titleField, flag){
            var self = this;
            var graph_data = false;
            if(chart_id){
                var id = '#' + chart_id;
                self.$el.find(id).empty();
            }
            if(pie_data){
                graph_data = pie_data;
            }
            if(pie_data.length > 0){
                var chart = AmCharts.makeChart(chart_id,{
                    "type": "pie",
                    "theme": "light",
                    "addClassNames": true,
                    "legend":{
                        "position":"bottom",
                        "marginRight":110,
                        "autoMargins":false
                    },
                    "innerRadius": "30%",
                    "defs": {
                        "filter": [{
                            "id": chart_id,
                            "width": "200%",
                            "height": "200%",
                            "feOffset": {
                                "result": "offOut",
                                "in": "SourceAlpha",
                                "dx": 0,
                                "dy": 0
                            },
                            "feGaussianBlur": {
                                "result": "blurOut",
                                "in": "offOut",
                                "stdDeviation": 5
                            },
                            "feBlend": {
                                "in": "SourceGraphic",
                                "in2": "blurOut",
                                "mode": "normal"
                            }
                        }]
                    },
                    "labelsEnabled": false,
                    "dataProvider"  : graph_data,
                    "valueField": value_field,
                    "titleField": titleField,
                    "legend" : false,
                    "export": {
                        "enabled": true
                    }
                });
            }
        },

        top_items_by_sales : function(company_id){
            var self = this;
            var option = $(".top_items_sales_w_m_y option:selected").attr('data-value');
            var start = moment().startOf(option).locale('en').format('YYYY-MM-DD');
            var end = moment().endOf(option).locale('en').format('YYYY-MM-DD');

            if(!option)
                option = 'week';

            this._rpc({
                model: 'pos.order',
                method: 'top_items_by_sales',
                args : [start, end, company_id ? Number(company_id): false]
            }).then(function(result) {
                self.$el.find('#top_items_sold').empty()
                if(result && result.length > 0){
                    $('#top_items_sold').DataTable({
                        lengthChange : false,
                        "responsive": false,
                        "destroy": true,
                        info: false,
                        pagingType: 'simple',
                        "pageLength": 3,
                        language: {
                            paginate: {
                                next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
                                previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
                            }
                        },
                        searching: false,
                        data: result,
                        columns: [
                            { title: "#" },
                            { title: "Products" },
                            { title: "Amount" },
                            { title: "Quantity" }
                        ]
                    });
                }else{
                    $(document).find('#top_items_sold').html('<div class="alert alert-info"><strong>No data found</strong></div>');
                }
            });
        },

        payment_by_journal_pie_chart_data : function(company_id){
            var self = this;
            this._rpc({
                model: 'pos.session',
                method: 'payment_by_journal_pie_chart',
                args : [company_id]
            }, {async: false}).then(function (res) {
                if(res){
                    var dps = [];
                    for(var i=0;i<res.length;i++){
                        dps.push({label: res[i].journal, amount: (res[i].amount).toFixed(2)});
                    }
                    self.prepare_pie_chart('journal_pie_chart' , dps, 'amount', 'label', {})
                }else{
                    $(document).find('#journal_pie_chart').empty();
                    $(document).find('#journal_pie_chart').append('<div class="alert alert-info"><strong><center>'
                                                                    +'No data found</center></strong></div>');
                }
            })
        },

        chart_journal : function(graph, data){
            var self = this;

            AmCharts.makeChart("journal_line_chart", {
              "type": "serial",
              "theme": "light",
              "titles": [{
                            "text": "Month of " + moment().locale('en').format('MMMM'),
                            "bold": true
                        }],
              "dataProvider":data,
              "valueAxes":[{
                            "gridColor": "#CC0000",
                          }],
              "gridAboveGraphs": true,
              "startDuration": 1,
              "graphs":graph,
              "chartCursor": {
                "categoryBalloonEnabled": false,
                "cursorAlpha": 0,
                "zoomable": false
              },
              "categoryField": "Date",
              "categoryAxis": {
                "gridPosition": "start",
                "gridAlpha": 0,
                "minorGridAlpha": 0.1,
                "gridAlpha": 0.15,
                "fillAlpha": 0.2,
                "dashLength": 0,
                "lineAlpha": 1,
              },
              "legend": {}
            });
        },

        on_change_journal: function (company_id) {
            var self = this;
            var select_journal = self.$el.find(".journal-option option:selected").attr('data-value');
            var start_month = moment().startOf('month').locale('en').format('YYYY-MM-DD');
            var end_month = moment().endOf('month').locale('en').format('YYYY-MM-DD');
            var company = self.$el.find(".pos-company option:selected").attr('data-id');
            if(company)
                company_id = company;

            this._rpc({
                model: 'pos.session',
                method: 'get_journal_line_chart_data',
                args : [start_month, end_month, select_journal, company_id]
            }, {async: false}).then(function (res) {
                if(res){
                    var source_data_list = res['data']
                    var graph_data = []
                    var graph_title = res['payment_method']
                    if(res['flag'] == true){
                        self.$el.find('.journal-option').empty()
                        self.$el.find('.journal-option').append('<option data-value="" select="selected">Select</option>')
                        $.each(graph_title, function(key, value) {
                            self.$el.find('.journal-option').append('<option data-value="' + value['id'] + '" data-id="'+ value['id']+'" >' + value['payment_method'] + '</option>');
                        });
                    }
                    $.each(graph_title, function(index, value) {
                        graph_data.push({
                            "title": value.payment_method,
                            "balloonText": "[[title]]: <b>[[value]]</b>",
                            "bullet": "round",
                            "bulletSize": 10,
                            "bulletBorderColor": "#ffffff",
                            "bulletBorderAlpha": 1,
                            "bulletBorderThickness": 2,
                            "valueField": value.payment_method.split(" ").join("_")
                        })
                    });
                    if(graph_data.length > 0){
                        self.chart_journal(graph_data, source_data_list);
                    }else{
                        $(document).find('#journal_line_chart').empty();
                        $(document).find('#journal_line_chart').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                    }
                }else{
                    $(document).find('#journal_line_chart').empty();
                    $(document).find('#journal_line_chart').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                }
            });
        },

        filter_by_d_m_y : function(e, company_id){
            var self = this;
            var company = self.$el.find(".pos-company option:selected").attr('data-id')
            if(company){
                company_id = company;
            }
            var filter_txt = $(e.currentTarget).attr('data-text')
            $(e.currentTarget).addClass("active");
            $(e.currentTarget).siblings().removeClass("active");

            if(filter_txt === 'year'){
                var start_year = moment().startOf('year').locale('en').format('YYYY-MM-DD');
                var end_year = moment().endOf('year').locale('en').format('YYYY-MM-DD');
                this._rpc({
                    model: 'pos.order',
                    method: 'sales_based_on_current_year',
                    args : [start_year, end_year, company_id]
                }, {async: false}).then(function (res) {
                    if(res['final_list'].length > 0){
                        self.dmy_chart(res['final_list'], 'order_month', 'Months',  "This Year Sale", "Sales : "+ res['currency']+"[[value]]", 'price_total')
                    }else{
                        $(document).find('#chart_day_month_year').empty();
                        $(document).find('#chart_day_month_year').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                    }
                });
            }else if(filter_txt === 'month'){
                var start_month = moment().startOf('month').locale('en').format('YYYY-MM-DD');
                var end_month = moment().endOf('month').locale('en').format('YYYY-MM-DD');

                this._rpc({
                    model: 'pos.order',
                    method: 'sales_based_on_current_month',
                    args : [start_month, end_month, company_id]
                }, {async: false}).then(function (res) {
                    if(res['final_list']){
                        if(res['final_list'].length > 0){
                            self.dmy_chart(res['final_list'], 'days', 'Days',  "This Month Sale", "Day :[[days]] Sales :"+res['currency']+"[[value]]")
                        }else{
                            $(document).find('#chart_day_month_year').empty();
                            $(document).find('#chart_day_month_year').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                        }
                    }
                });
            }else{
                var today = moment().locale('en').format('YYYY-MM-DD');
                this._rpc({
                    model: 'pos.order',
                    method: 'sales_based_on_hours',
                    args : [today,today, company_id]
                }, {async: false}).then(function (result) {
                    var hrs_pay_data = []
                    var res = result['pos_order']
                    for(var i=0;i<res['sales_based_on_hours'].length;i++){
                        hrs_pay_data.push({'hours': res['sales_based_on_hours'][i].date_order_hour[0] + '-' + res['sales_based_on_hours'][i].date_order_hour[1], 'price': res['sales_based_on_hours'][i].price_total, 'quantity': res['sales_based_on_hours'][i].quantity});
                    }
                    var hour = ''
                    if(result['top_hour']['top_hour'] == 0){
                        hour = result['top_hour']['top_hour']
                    }else{
                        hour = result['top_hour']['top_hour'] + 1
                    }
                    self.$el.find('#top_hours_hour').html('Amount : ' + result['currency'] + result['top_hour']['amount'] || 0.0)
                    self.$el.find('#top_hour_amount').html(result['top_hour']['top_hour'] + " - " + hour)

                    if(hrs_pay_data.length > 0){
                        self.dmy_chart(hrs_pay_data, 'hours','Hours' ,"Today's Hourly Sale", 'Sales : '+ result['currency']+' [[value]]')
                    }else{
                        $(document).find('#chart_day_month_year').empty();
                        self.$el.find('#top_hours_hour').empty()
                        self.$el.find('#top_hour_amount').empty()
                        $(document).find('#chart_day_month_year').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                    }
                })
            }
        },

        dmy_chart : function(graph_data, graph_text, graph_title, title, baloon_text, price_total){
            var self = this;
            var flag = false;
            if(graph_text==='hours'){
                flag = true;
            }
            if(graph_data){
                self.$el.find('#chart_day_month_year').empty();
            }
            if(graph_data.length > 0){
                var chart1 = AmCharts.makeChart( "chart_day_month_year", {
                    "type": "serial",
                    "theme": "light",
                    "marginRight": 0,
                    "titles": [{
                        "text": title,
                    }],
                    "rotate": false,
                    "dataProvider": graph_data,
                    "startDuration": 1,
                    "graphs": [ {
                        "balloonText": baloon_text,
                        "fillAlphas": 0.8,
                        "lineAlpha": 0.2,
                        "title": title,
                        "type": "column",
                        "valueField": price_total || "price",
                        "autoColor": false
                    }],
                    "guides": [],
                    "chartCursor": {
                        "categoryBalloonEnabled": false,
                        "cursorAlpha": 0,
                        "zoomable": false
                    },
                    "categoryField": graph_text,
                    "categoryAxis": {
                         "parseDates" : false,
                         "gridPosition": "start",
                         "ignoreAxisWidth": true,
                         "position": "bottom",
                         "labelsEnabled":true,
                         "title":graph_title,
                         "autoGridCount": flag,
                         "gridCount": 31
                    },
                    "valueAxes": [
                        {
                            "position": "left",
                            "title": "Price",
                            "axisAlpha": 0,
                            "inside": false,
                        }
                    ],
                    "allLabels":[
                        {
                            "text": graph_text,
                            "align": "bottom",
                            "x": "400",
                            "y": "650",
                            "width": "50%",
                            "size": 14,
                            "bold": true,
                            "inside": false,
                        }
                    ],
                    "marginBottom": 75,
                    "dataProvider": graph_data,
                    "export": {
                        "enabled": true
                    }
                } );
            }
        },

        daily_gross_sales_line_chart : function(source_data, today, last){
            var chart = AmCharts.makeChart("daily_gross_sale", {
                "type": "serial",
                "theme": "light",
                "dataProvider": source_data,
                "valueAxes": [
                    {
                        "gridColor": "#CC0000",
                    }
                ],
                "gridAboveGraphs": true,
                "startDuration": 1,
                "graphs": [
                    {
                        "title": today,
                        "balloonText": "[[title]]: <b>[[value]]</b>",
                        "bullet": "round",
                        "bulletSize": 10,
                        "bulletBorderColor": "#ffffff",
                        "bulletBorderAlpha": 1,
                        "bulletBorderThickness": 2,
                        "valueField": "today"
                    },
                    {
                        "title": last,
                        "balloonText": "[[title]]: <b>[[value]]</b>",
                        "bullet": "round",
                        "bulletSize": 10,
                        "bulletBorderColor": "#ffffff",
                        "bulletBorderAlpha": 1,
                        "bulletBorderThickness": 2,
                        "valueField": "last"
                    },
                ],
                "chartCursor": {
                        "categoryBalloonEnabled": false,
                        "cursorAlpha": 0,
                        "zoomable": false
                },
                "categoryField": "hours",
                "categoryAxis": {
                    "gridPosition": "start",
                    "gridAlpha": 0,
                    "minorGridAlpha": 0.1,
                    "minorGridEnabled": true,
                    "gridAlpha": 0.15,
                    "dashLength": 0,
                    "lineAlpha": 1,
                    "fillAlpha": 0.2,
                },
                "legend": {
                    'align':'right',
                    'position':'top'
                }
            });
        },

        daily_gross_sales: function(company_id){
            var self = this;
            var today = moment().locale('en').format('YYYY-MM-DD');
            var last_today_day = moment().subtract(7, "days").locale('en').format('YYYY-MM-DD');

            var weekDayNameToday =  moment(today).locale('en').format('dddd');
            var weekDayNameLastToday =  moment(last_today_day).locale('en').format('dddd');

            this._rpc({
                model: 'pos.order',
                method: 'daily_gross_sales',
                args : [today, last_today_day, company_id]
            }, {async: false}).then(function (res) {
                var hrs_pay_data = []
                var today_day = moment().locale('en').format('dddd, MMMM Do YYYY');
                var last_day = moment().subtract(7, "days").locale('en').format('dddd, MMMM Do YYYY');
                if(res['sales_based_on_hours'] && res['sales_based_on_hours'].length > 0){
                    for(var i=0;i<res['sales_based_on_hours'].length;i++){
                        hrs_pay_data.push({
                            'hours': res['sales_based_on_hours'][i].date_order_hour[0],
                            'today': res['sales_based_on_hours'][i].today,
                            'last': res['sales_based_on_hours'][i].last
                        });
                    }
                    self.daily_gross_sales_line_chart(hrs_pay_data, today_day, last_day)
                }else{
                    $(document).find('#daily_gross_sale').empty();
                    $(document).find('#daily_gross_sale').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                }
            })
        },

        weekly_gross_sales_compare_bar_chart(data_provider, start, end){
            var self = this;
            if(data_provider){
                self.$el.find('#weekly_gross_date').empty();
                self.$el.find('#weekly_gross_date').append('<i class="fa fa-circle" style="color: rgb(103, 183, 220);"> &nbsp;' + start + '</i><br/><i class="fa fa-circle" style="color: #A9A9A9;">&nbsp;' + end +'</i>')
            }
            var chart = AmCharts.makeChart("weekly_gross_sales_compare_barchart", {
                "type": "serial",
                 "theme": "light",
                "categoryField": "day",

                "startDuration": 1,
                "categoryAxis": {
                    "gridPosition": "start",
                    "position": "left"
                },
                "trendLines": [],
                "graphs": [
                    {
                        "balloonText": "Sales:[[value]]",
                        "fillAlphas": 0.8,

                        "id": "AmGraph-1",
                        "lineAlpha": 0.2,
                        "title": start,
                        "type": "column",
                        "valueField": "current_week"
                    },
                    {
                        "balloonText": "Sales :[[value]]",
                        "fillColors": "#A9A9A9",
                        "fillAlphas": 0.8,
                        "id": "AmGraph-2",
                        "lineAlpha": 0.2,
                        "title": end,
                        "type": "column",
                        "valueField": "last_week"
                    }
                ],
                "guides": [],
                "valueAxes": [
                    {
                        "id": "ValueAxis-1",
                        "axisAlpha": 0
                    }
                ],
                "allLabels": [],
                "balloon": {},
                "titles": [],
                "dataProvider": data_provider,
                "export": {
                    "enabled": true
                 }
            });
        },

        weekly_gross_salse : function(company_id){
            var self = this;
            var current_week_start_date = moment().startOf('week').locale('en').format('YYYY-MM-DD');
            var current_week_end_date = moment().endOf('week').locale('en').format('YYYY-MM-DD');
            var last_week_start_date = moment().subtract(1, 'weeks').startOf('week').locale('en').format('YYYY-MM-DD');
            var last_week_end_date = moment().subtract(1, 'weeks').endOf('week').locale('en').format('YYYY-MM-DD');

            this._rpc({
                model: 'pos.order',
                method: 'weekly_gross_sales',
                args : [current_week_start_date, current_week_end_date, last_week_start_date, last_week_end_date, company_id]
            }, {async: false}).then(function (res) {
                if(res && res['weekly_compare_sales'].length > 0){
                    var this_week = [moment(current_week_start_date).locale('en').format('MMM.DD') + ' - ' + moment(current_week_end_date).locale('en').format('MMM.DD')]
                    var las_week = [moment(last_week_start_date).locale('en').format('MMM.DD') + ' - ' + moment(last_week_end_date).locale('en').format('MMM.DD')]
                    self.weekly_gross_sales_compare_bar_chart(res['weekly_compare_sales'], this_week, las_week)
                }else{
                    $(document).find('#daily_gross_sale').empty();
                    $(document).find('#daily_gross_sale').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                }
            });
        },

        onchange_week_option : function(company_id, option){
            var self = this;
            var select_week = self.$el.find(".week-option option:selected").val();
            if(option){
                select_week = option;
            }
            var first = moment().locale('en').day("Sunday").week(select_week).format('YYYY-MM-DD');
            var last = moment().locale('en').day("Saturday").week(select_week).format('YYYY-MM-DD');

            var company = self.$el.find(".pos-company option:selected").attr('data-id')
            if(company){
                company_id = company;
            }
            this._rpc({
                model: 'pos.order',
                method: 'sales_data_per_week',
                args : [first, last, company_id]
            }, {async: false}).then(function (res) {
                var data_provider = [];
                if(res.length > 0){
                    for(var i=0;i<res.length;i++){
                        data_provider.push({
                            'order_count':res[i].count,
                            'day':res[i].day,
                            'sale_total':res[i].sale_total
                        })
                    }
                    var chart = AmCharts.makeChart("chartweekly", {
                        "type": "serial",
                        "theme": "light",
                        "legend": {
                            "equalWidths": false,
                            "useGraphSettings": true,
                            "valueAlign": "left",
                            "valueWidth": 120
                        },
                        "dataProvider": data_provider,
                        "valueAxes": [{
                            "id": "sale_totalAxis",
                            "axisAlpha": 0,
                            "gridAlpha": 0,
                            "position": "left",
                            "title": "Sale"
                        },{
                            "id": "order_countAxis",
                            "axisAlpha": 0,
                            "gridAlpha": 0,
                            "integersOnly":true,
                            "position": "right",
                            "title": "Orders"
                        }],
                        "graphs": [{
                            "alphaField": "alpha",
                            "balloonText": "[[value]]",
                            "dashLengthField": "dashLength",
                            "fillAlphas": 0.7,
                            "legendPeriodValueText": ": [[value.sum]]",
                            "legendValueText": ": [[value]]",
                            "title": "Sale",
                            "type": "column",
                            "valueField": "sale_total",
                            "valueAxis": "sale_totalAxis"
                        },{
                            "bullet": "square",
                            "bulletBorderAlpha": 1,
                            "bulletBorderThickness": 1,
                            "dashLengthField": "dashLength",
                            "legendValueText": ": [[value]]",
                            "legendPeriodValueText": ": [[value.sum]]",
                            "title": "Orders",
                            "valueField": "order_count",
                            "valueAxis": "order_countAxis"
                        }],
                        "chartCursor": {
                            "cursorAlpha": 0.1,
                            "cursorColor":"#000000",
                            "fullWidth":true,
                            "valueBalloonsEnabled": false,
                            "zoomable": false
                        },
                        "categoryField": "day",
                        "categoryAxis": {
                            "autoGridCount": false,
                            "axisColor": "#555555",
                            "gridAlpha": 0.1,
                            "gridColor": "#FFFFFF",
                            "gridCount": 50
                        },
                        "export": {
                            "enabled": true
                         }
                    });
                }else{
                    $(document).find('#chartweekly').empty();
                    $(document).find('#chartweekly').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                }
            });
        },

        onchange_month_option : function(){
            var self = this;
            var select_month = self.$el.find(".month-option option:selected").val();
            var firstDayOfMonth = moment(String(moment().year())+'-'+select_month+"'", 'YYYY-MM-DD');
            const numOfDays = firstDayOfMonth.daysInMonth();
            let weeks = new Set();
            for(let i = 0; i < numOfDays; i++){
                const currentDay = moment(firstDayOfMonth, 'YYYY-MM-DD').add(i, 'days');
                weeks.add(currentDay.isoWeek());
            }
            var week = moment().isoWeek()
            var week_option = $(document).find('.week-option');
            week_option.empty();
            var res = Array.from(weeks)
            for(var i=0;i<res.length;i++){
                if(res[i] ==week){
                    week_option.append('<option selected="selected" value="' + res[i] + '" data-id="'+ res[i]+'" >' + 'Week-'+res[i]+ '</option>');
                    break
                }
//                else if(res[i] > week){
//                    break
//                }
                week_option.append('<option value="' + res[i] + '" data-id="'+ res[i]+'" >' + 'Week-'+res[i]+ '</option>');
            }
            var select_week = self.$el.find(".week-option option:selected").val();
            self.onchange_week_option('', select_week)
        },

        get_top_product_category : function(company_id){
            var self = this;
            var selected_option = $(".product-option option:selected").val();
            var selected_order = $(".product-order option:selected").val();
            var option = $(".top_product_catg_w_m_y option:selected").attr('data-value')
            var start = moment().startOf(option).locale('en').format('YYYY-MM-DD');
            var end = moment().endOf(option).locale('en').format('YYYY-MM-DD');

            if (!Number.isInteger(company_id)){
                    company_id = self.$el.find('.pos-company option:selected').attr('data-id')
            }
            if(!option){
                option = 'week'
            }
            this._rpc({
                model: 'pos.order',
                method: 'products_category',
                args : [start, end, selected_order, selected_option, company_id]
            }, {async: false}).then(function (res) {
                if(res['data_source'] && res['data_source'].length > 0){
                    var chart = AmCharts.makeChart("top_product_category", {
                        "type": "pie",
                        "theme": "light",
                        "dataProvider":res['data_source'],
                        "titleField": "category" ,
                        "valueField": "value",
                        "labelRadius": 5,
                        "radius": "42%",
                        "innerRadius": "60%",
                        "labelText": "",
                        "legend": {
                            "position":"right",
                            "align" : "top",
                            "marginRight":100,
                            "autoMargins":false
                         },
                        "export": {
                            "enabled": true
                        }
                    } );
                }else{
                    $(document).find('#top_product_category').empty();
                    $(document).find('#top_product_category').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                }
            });
        },

        employee_work_hour : function(company_id){
            var self = this;
//            setTimeout(function(){
                var first = moment().startOf('week').locale('en').format('YYYY-MM-DD');
                var last = moment().endOf('week').locale('en').format('YYYY-MM-DD');
                this._rpc({
                    model: 'pos.order',
                    method: 'employee_work_hour',
                    args : [first, last, company_id]
                }, {async: false}).then(function (res) {
                    if(res){
                        var contents = self.$el.find('.employee_time');
                        contents.empty();
                        var dataSet = []
                        var img = ''
                        for(var i=0;i<res.length;i++){
                            if(res[i].eimage){
                                img = "<img class='rounded-circle' src='data:image/png;base64," + res[i].eimage +"' width='30' height='30'/> "
                            }else{
                                img = "<i class='fa fa-user' style='font-size:27px;'></i>"
                            }
                            dataSet.push([ img, res[i].ename, Number(res[i].total_time) ])
                        }
                        if(dataSet.length > 0){
                            $('.employee_time').DataTable({
                                "lengthChange" : false,
                                "destroy": true,
                                "info": false,
                                "responsive": false,
                                "pagingType": 'simple',
                                "pageLength": 3,
                                "language": {
                                    "paginate":{
                                        next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
                                        previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
                                    }
                                },
                                searching: false,
                                data: dataSet,
                                columns: [
                                            { title: "" },
                                            { title: "Employee" },
                                            { title: "Working Hour" },
                                        ]
                               });
                        }else{
                            $(document).find('.employee_time').empty();
                            $(document).find('.employee_time').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                        }
                    }else{
                        $(document).find('.employee_time').empty();
                        $(document).find('.employee_time').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                    }
                });
//            });
        },

        sales_per_salesperson : function(company_id){
            var self = this;
            setTimeout(function(){
                var option = $(".top_salesman_w_m_y option:selected").attr('data-value')
                if (!Number.isInteger(company_id)){
                    company_id = self.$el.find('.pos-company option:selected').attr('data-id')
                }
                if(!option){
                    option = 'week'
                }

                var start = moment().startOf(option).locale('en').format('YYYY-MM-DD');
                var end = moment().endOf(option).locale('en').format('YYYY-MM-DD');
                rpc.query({
                    model: 'pos.order',
                    method: 'sales_data_per_salesperson',
                    args : [start, end, company_id]
                }, {async: false}).then(function (result) {
                    if(result){
                        var res = result['salesperson_data']
                        var contents = self.$el.find('.top_salesperson');
                        contents.empty();
                        var dataSet = []
                        var top_salesperson_data = res['salesperson_data']
                        self.$el.find('#top_staff_today_amount').html('Amount : ' + result['currency'] + result['top_staff']['amount'])
                        self.$el.find('#top_staff_today_name').html(result['top_staff']['top_staff'])
                        var img = '';
                        for(var i=0;i < res.length;i++){
                            if(res[i].person_image){
                                img = "<img class='rounded-circle' src='data:image/png;base64,"+ res[i].person_image +"' width='30' height='30'> "
                            }else{
                                img = "<i class='fa fa-user' style='font-size:27px;'></i>"
                            }
                           dataSet.push([img, res[i].person_name, Number(res[i].num_order), result['currency'] +' '+ res[i].amount])
                        }
                        if(dataSet.length > 0){
                            $('.top_salesperson').DataTable( {
                            lengthChange : false,
                            info: false,
                            pagingType: 'simple',
                            "responsive": false,
                            "destroy": true,
                            "pageLength": 5,
                            language: {
                                paginate: {
                                    next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
                                    previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
                                }
                            },
                            searching: false,
                            data: dataSet,
                            columns: [
                                    { title: "" },
                                    { title: "Name" },
                                    { title: "Orders" },
                                    { title: "Amount" },
                                ]
                            });
                        }else{
                            $(document).find('.top_salesperson').empty();
                            $(document).find('.top_salesperson').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                        }
                    }else{
                        self.$el.find('#top_staff_today_amount').empty()
                        self.$el.find('#top_staff_today_amount').append('0.0')
                        self.$el.find('#top_staff_today_name').empty()
                        self.$el.find('#top_staff_today_name').append('No Data Found')
                        $(document).find('.top_salesperson').empty();
                        $(document).find('.top_salesperson').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                    }
                });
            });
        },

        avg_selling_price : function (company_id){
            var self = this;
            var start_date = moment().locale('en').format('YYYY-MM-DD');
            var end_date = moment().subtract(30, 'days').locale('en').format('YYYY-MM-DD');

            this._rpc({
                model: 'pos.order',
                method: 'avg_selling_price',
                args : [company_id]
            }, {async: false}).then(function (res) {
                self.$el.find("#average-selling-price").html(self.format_currency(res['avg_selling_price']|| 0.0));
                self.$el.find(".average-selling-price-icon").html(res['currency_icon'] || '<i fa class="fa-dollar"></i>')
            })
        },

        customer_avg_visit : function (company_id){
            var self = this;
            rpc.query({
                model: 'pos.order',
                method: 'highest_selling_day_from_last_30_days',
                args : [company_id]
            }, {async: false}).then(function (res) {
                let formatted_amount = self.format_currency(res.length > 0 ? res[0].amount : 0.0);
                self.$el.find("#highest_sales_last_30_days").html(formatted_amount);
            })
        },

        get_top_customer : function(company_id){
            var self = this;
            var option = $(".top_customer_w_m_y option:selected").attr('data-value')
            if (!Number.isInteger(company_id)){
                company_id = self.$el.find('.pos-company option:selected').attr('data-id')
            }
            if(!option){
                option = 'week'
            }
            var start = moment().startOf(option).locale('en').format('YYYY-MM-DD');
            var end = moment().endOf(option).locale('en').format('YYYY-MM-DD');

            this._rpc({
                model: 'pos.order',
                method: 'get_the_top_customer',
                args : [start, end, company_id]
            }, {async: false}).then(function (result) {
                if(result){
                    var contents = self.$el.find('.top-client');
                    contents.empty();
                    var res = result['top_customer'];
                    var dataSet = [];
                    for(var i=0;i<res.length;i++){
                        dataSet.push([res[i].customer, res[i].total_product,'<span class="label label-success">' + result['currency'] +' '+res[i].amount + '</span>'])
                    }
                    if(dataSet.length > 0){
                        $('.top-client').DataTable( {
                            lengthChange : false,
                            info: false,
                            "destroy": true,
                            "responsive": false,
                            pagingType: 'simple',
                            "pageLength": 4,
                            language: {
                                paginate: {
                                    next: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-right" /></button>',
                                    previous: '<button type="button" class="btn btn-box-tool"><i class="fa fa-angle-left" /></button>'
                                }
                            },
                            searching: false,
                            data: dataSet,
                            columns: [
                                { title: "Customer" },
                                { title: "Products" },
                                { title: "Amount" }
                            ]
                        });
                    }else{
                        $(document).find('.top-client').empty();
                        $(document).find('.top-client').append('<div class="alert alert-info"><strong><center>No data found</center></strong></div>');
                    }
                }
            });
        },

        header_data : function(company_id){
            var self = this;
            this._rpc({
                model: 'pos.session',
                method: 'get_active_session',
                args :[moment().locale('en').format('YYYY-MM-DD'), moment().locale('en').format('YYYY-MM-DD'), company_id]
            }, {async: false}).then(function (res) {
                if(res){
                    self.$el.find('.pos_session').empty();
                    res['session'].length > 1 ? self.$el.find('.pos_session').append('<i class="fa fa-users"/>'):
                                                self.$el.find('.pos_session').append('<i class="fa fa-user"/>');
                    if(res['login_user_img']){
                        self.$el.find('#image_viewer').html('<img class="rounded-circle" style="width:70px" src="data:image/jpeg;base64,'+res['login_user_img']+'"/>');
                    }else{
                         self.$el.find('#image_viewer').html('<img class="rounded-circle" src="aspl_pos_backend_dashboard/static/src/images/avtar.png">');
                    }
                    self.$el.find('.welcome-text').html(res['login_user']);
                    self.$el.find('.active-session').text(res['session']);
                    self.$el.find('.total-orders').text(res['order']);
                    self.$el.find('.total-sales').text(res['total_sale']);
                    self.$el.find('.product-sold').text(res['product_sold']);
                    self.$el.find('.today-total-sales').text(res['today_sales']);
                    self.$el.find('.today-total-orders').text(res['today_order']);
                    self.$el.find('.today-product-sold').text(res['today_product']);
                }
            });
        },
        renderElement: function () {
            var self = this;
            this._super.apply(this, arguments);
            var month = moment().month() + 1
            var week = moment().isoWeek();

            var temp = self.$el.find('.week-option');
            self.$el.find('.month-option option[value='+String(month)+']').attr('selected', 'selected');
            self.$el.find('.week-option option[value='+String(week)+']').attr('selected', 'selected');
            const firstDayOfMonth = moment(String(moment().year())+'-'+month+"'", 'YYYY-MM-DD');
            const numOfDays = firstDayOfMonth.daysInMonth();
            let weeks = new Set();

            for(let i = 0; i < numOfDays; i++){
                const currentDay = moment(firstDayOfMonth, 'YYYY-MM-DD').add(i, 'days');
                weeks.add(currentDay.isoWeek());
            }
            temp.empty();

            var res = Array.from(weeks);
            for(var i=0; i<res.length; i++){
                if(res[i] ==week || res[i] > week){
                    temp.append('<option selected="selected" value="' + res[i] + '" data-id="'+ res[i]+'" >' + 'Week-'+res[i]+ '</option>');
                    break;
                }else if(res[i] > week){
                    break;
                }
                temp.append('<option value="' + res[i] + '" data-id="'+ res[i]+'" >' + 'Week-'+res[i]+ '</option>');
            }

            setTimeout(function(){
                self.header_data();
                self.filter_by_d_m_y('', '');
                self.sales_per_salesperson();
                self.payment_by_journal_pie_chart_data()
                self.customer_avg_visit()
                self.employee_work_hour();
                self.top_items_by_sales();
                self.get_top_customer()
                self.get_top_product_category();
                self.on_change_journal();
                self.onchange_week_option();
                self.daily_gross_sales();
                self.avg_selling_price()
                self.weekly_gross_salse();
            },0)
        },
    });
    core.action_registry.add('pos_sales_dashboard', POSDashboard);
    return {
        POSDashboard : POSDashboard,
    };
});
