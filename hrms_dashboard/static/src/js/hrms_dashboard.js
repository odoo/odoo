console.log("starting");
odoo.define('hrms_dashboard.DashboardRewrite', function (require) {
"use strict";
console.log("started");
const ActionMenus = require('web.ActionMenus');
const ComparisonMenu = require('web.ComparisonMenu');
const ActionModel = require("web.ActionModel");
const FavoriteMenu = require('web.FavoriteMenu');
const FilterMenu = require('web.FilterMenu');
const GroupByMenu = require('web.GroupByMenu');
const Pager = require('web.Pager');
const SearchBar = require('web.SearchBar');
const { useModel } = require('web.Model');
const { Component, hooks } = owl;

var concurrency = require('web.concurrency');
var config = require('web.config');
var field_utils = require('web.field_utils');
var time = require('web.time');
var utils = require('web.utils');
var AbstractAction = require('web.AbstractAction');
var ajax = require('web.ajax');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');
var core = require('web.core');
var rpc = require('web.rpc');
var session = require('web.session');
var web_client = require('web.web_client');
var abstractView = require('web.AbstractView');
var _t = core._t;
var QWeb = core.qweb;

const { useRef, useSubEnv } = owl;


var HrDashboard = AbstractAction.extend({
    template: 'HrDashboardMain',
    cssLibs: [
        '/hrms_dashboard/static/src/css/lib/nv.d3.css'
    ],
    jsLibs: [
        '/hrms_dashboard/static/src/js/lib/d3.min.js'
    ],

     events: {
             'click .hr_leave_request_approve': 'leaves_to_approve',
             'click .hr_leave_allocations_approve': 'leave_allocations_to_approve',
             'click .hr_job_application_approve': 'job_applications_to_approve',
             'click .leaves_request_today':'leaves_request_today',
             'click .leaves_request_month':'leaves_request_month',
             'click .hr_payslip':'hr_payslip',
             'click .hr_contract':'hr_contract',
             'click .hr_timesheets': 'hr_timesheets',
             'click .login_broad_factor': 'employee_broad_factor',
            "click .o_hr_attendance_sign_in_out_icon": function() {
            this.$('.o_hr_attendance_sign_in_out_icon').attr("disabled", "disabled");
            this.update_attendance();
        },
        'click #broad_factor_pdf': 'generate_broad_factor_report',


    },



    init: function(parent, context) {

        this._super(parent, context);
        this.date_range = 'week';  // possible values : 'week', 'month', year'
        this.date_from = moment().subtract(1, 'week');
        this.date_to = moment();
        this.dashboards_templates = ['LoginEmployeeDetails','ManagerDashboard', 'EmployeeDashboard'];
        this.employee_birthday = [];
        this.upcoming_events = [];
        this.announcements = [];
        this.login_employee = [];

    },

    willStart: function(){
        var self = this;
        this.login_employee = {};
        return this._super()
        .then(function() {
            var def0 =  self._rpc({
                    model: 'hr.employee',
                    method: 'check_user_group'
            }).then(function(result) {
                if (result == true){
                    self.is_manager = true;
                }
                else{
                    self.is_manager = false;
                }
            });
            var def1 =  self._rpc({
                    model: 'hr.employee',
                    method: 'get_user_employee_details'
            }).then(function(result) {
                self.login_employee =  result[0];
            });
            var def2 = self._rpc({
                model: "hr.employee",
                method: "get_upcoming",
            })
            .then(function (res) {
                self.employee_birthday = res['birthday'];
                self.upcoming_events = res['event'];
                self.announcements = res['announcement'];
            });
        return $.when(def0, def1, def2);
        });
    },

    start: function() {

            var self = this;
            this.set("title", 'Dashboard');
            return this._super().then(function() {
                self.update_cp();
                self.render_dashboards();
                self.render_graphs();
                self.$el.parent().addClass('oe_background_grey');
            });
        },

    fetch_data: function() {
        var self = this;
        var def0 =  self._rpc({
                model: 'hr.employee',
                method: 'check_user_group'
        }).then(function(result) {
            if (result == true){
                self.is_manager = true;
            }
            else{
                self.is_manager = false;
            }
        });
        var def1 =  this._rpc({
                model: 'hr.employee',
                method: 'get_user_employee_details'
        }).then(function(result) {
            self.login_employee =  result[0];
        });
        var def2 = self._rpc({
            model: "hr.employee",
            method: "get_upcoming",
        })
        .then(function (res) {
            self.employee_birthday = res['birthday'];
            self.upcoming_events = res['event'];
            self.announcements = res['announcement'];
        });
        return $.when(def0, def1, def2);
    },


    render_dashboards: function() {
        var self = this;
        if (this.login_employee){
            var templates = []
            if( self.is_manager == true){templates = ['LoginEmployeeDetails','ManagerDashboard', 'EmployeeDashboard'];}
            else{ templates = ['LoginEmployeeDetails', 'EmployeeDashboard'];}
            _.each(templates, function(template) {
                self.$('.o_hr_dashboard').append(QWeb.render(template, {widget: self}));
            });
        }
        else{
                self.$('.o_hr_dashboard').append(QWeb.render('EmployeeWarning', {widget: self}));
            }
    },

    render_graphs: function(){
        var self = this;
        if (this.login_employee){
            self.render_department_employee();
            self.render_leave_graph();
            self.update_join_resign_trends();
            self.update_monthly_attrition();
            self.update_leave_trend();
        }
    },

    on_reverse_breadcrumb: function() {
        var self = this;
        web_client.do_push_state({});
        this.update_cp();
        this.fetch_data().then(function() {
            self.$('.o_hr_dashboard').empty();
            self.render_dashboards();
            self.render_graphs();
        });
    },

    update_cp: function() {
        var self = this;
    },

    get_emp_image_url: function(employee){
        return window.location.origin + '/web/image?model=hr.employee&field=image_1920&id='+employee;
    },

    update_attendance: function () {
        var self = this;
        this._rpc({
            model: 'hr.employee',
            method: 'attendance_manual',
            args: [[self.login_employee.id], 'hr_attendance.hr_attendance_action_my_attendances'],
        })
        .then(function(result) {
            var attendance_state =self.login_employee.attendance_state;
            var message = ''
            var action_client = {
                type: "ir.actions.client",
                name: _t('Dashboard '),
                tag: 'hr_dashboard',
            };
            self.do_action(action_client, {clear_breadcrumbs: true});
            if (attendance_state == 'checked_in'){
                message = 'Checked Out'
            }
            else if (attendance_state == 'checked_out'){
                message = 'Checked In'
            }
            self.trigger_up('show_effect', {
                message: _t("Successfully " + message),
                type: 'rainbow_man'
            });
        });

    },

     //events

        hr_payslip: function(ev){
            var self = this;
            ev.stopPropagation();
            ev.preventDefault();
//            var $action = $(ev.currentTarget);


            var options = {
                on_reverse_breadcrumb: this.on_reverse_breadcrumb,
            };

            this.do_action({
                name: _t("Employee Payslips"),
                type: 'ir.actions.act_window',
                res_model: 'hr.payslip',
                view_mode: 'tree,form,calendar',
                views: [[false, 'list'],[false, 'form']],
                domain: [['employee_id','=', this.login_employee.id]],
                target: 'current' //self on some of them
            }, {
                    on_reverse_breadcrumb: this.on_reverse_breadcrumb
            });
        },

        leaves_to_approve: function(e) {

        var self = this;
        e.stopPropagation();
        e.preventDefault();

        var options = {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        };
        this.do_action({
            name: _t("Leave Request"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            view_mode: 'tree,form,calendar',
            views: [[false, 'list'],[false, 'form']],
            domain: [['state','in',['confirm','validate1']]],
            target: 'current'
        }, options)
    },

    //employee broad factor

    employee_broad_factor: function(e) {

        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var options = {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        };
        var today = new Date();

        var dd = String(today.getDate()).padStart(2, '0');
        var mm = String(today.getMonth() + 1).padStart(2, '0'); //January is 0!
        var yyyy = today.getFullYear();

//        today = mm + '/' + dd + '/' + yyyy;

        this.do_action({
            name: _t("Leave Request"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            view_mode: 'tree,form,calendar',
            views: [[false, 'list'],[false, 'form']],
            domain: [['state','in',['validate']],['employee_id','=', this.login_employee.id],['date_to','<=',today]],
            target: 'current',
            context:{'order':'duration_display'}
        }, options)

    },

    //hr timesheets

    hr_timesheets: function(e) {
         var self = this;
        e.stopPropagation();
        e.preventDefault();
        var options = {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        };
        this.do_action({
            name: _t("Timesheets"),
            type: 'ir.actions.act_window',
            res_model: 'account.analytic.line',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            context: {
                'search_default_month': true,
            },
            domain: [['employee_id','=', this.login_employee.id]],
            target: 'current'
        }, options)
    },

    //Contracts

    hr_contract: function(e){
            var self = this;
            e.stopPropagation();
            e.preventDefault();
            session.user_has_group('hr.group_hr_manager').then(function(has_group){
                if(has_group){
                    var options = {
                        on_reverse_breadcrumb: self.on_reverse_breadcrumb,
                    };
                    self.do_action({
                        name: _t("Contracts"),
                        type: 'ir.actions.act_window',
                        res_model: 'hr.contract',
                        view_mode: 'tree,form,calendar',
                        views: [[false, 'list'],[false, 'form']],
                        context: {
                            'search_default_employee_id': self.login_employee.id,
                        },
                        target: 'current'
                    })
                }
            });

        },

    //leave request today
    leaves_request_today: function(e) {
        var self = this;
        var date = new Date();
        e.stopPropagation();
        e.preventDefault();
        var options = {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        };
        this.do_action({
            name: _t("Leaves Today"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            view_mode: 'tree,form,calendar',
            views: [[false, 'list'],[false, 'form']],
            domain: [['date_from','<=', date], ['date_to', '>=', date], ['state','=','validate']],
            target: 'current'
        }, options)
    },

    //leave requests this month

    leaves_request_month: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var options = {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        };
        var date = new Date();
        var firstDay = new Date(date.getFullYear(), date.getMonth(), 1);
        var lastDay = new Date(date.getFullYear(), date.getMonth() + 1, 0);
        var fday = firstDay.toJSON().slice(0,10).replace(/-/g,'-');
        var lday = lastDay.toJSON().slice(0,10).replace(/-/g,'-');
        this.do_action({
            name: _t("This Month Leaves"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave',
            view_mode: 'tree,form,calendar',
            views: [[false, 'list'],[false, 'form']],
            domain: [['date_from','>', fday],['state','=','validate'],['date_from','<', lday]],
            target: 'current'
        }, options)
    },

    leave_allocations_to_approve: function(e) {
        var self = this;
        e.stopPropagation();
        e.preventDefault();
        var options = {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        };
        this.do_action({
            name: _t("Leave Allocation Request"),
            type: 'ir.actions.act_window',
            res_model: 'hr.leave.allocation',
            view_mode: 'tree,form,calendar',
            views: [[false, 'list'],[false, 'form']],
            domain: [['state','in',['confirm', 'validate1']]],
            target: 'current'
        }, options)
    },

    job_applications_to_approve: function(event){
        var self = this;
        event.stopPropagation();
        event.preventDefault();
        var options = {
            on_reverse_breadcrumb: this.on_reverse_breadcrumb,
        };
        this.do_action({
            name: _t("Applications"),
            type: 'ir.actions.act_window',
            res_model: 'hr.applicant',
            view_mode: 'tree,kanban,form,pivot,graph,calendar',
            views: [[false, 'list'],[false, 'kanban'],[false, 'form'],
                    [false, 'pivot'],[false, 'graph'],[false, 'calendar']],
            context: {},
            target: 'current'
        }, options)
    },

    //End Events


    render_department_employee:function(){
        var self = this;
        var w = 200;
        var h = 200;
        var r = h/2;
        var elem = this.$('.emp_graph');
//        var colors = ['#ff8762', '#5ebade', '#b298e1', '#70cac1', '#cf2030'];
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
        '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);
        rpc.query({
            model: "hr.employee",
            method: "get_dept_employee",
        }).then(function (data) {
            var segColor = {};
            var vis = d3.select(elem[0]).append("svg:svg").data([data]).attr("width", w).attr("height", h).append("svg:g").attr("transform", "translate(" + r + "," + r + ")");
            var pie = d3.layout.pie().value(function(d){return d.value;});
            var arc = d3.svg.arc().outerRadius(r);
            var arcs = vis.selectAll("g.slice").data(pie).enter().append("svg:g").attr("class", "slice");
            arcs.append("svg:path")
                .attr("fill", function(d, i){
                    return color(i);
                })
                .attr("d", function (d) {
                    return arc(d);
                });

            var legend = d3.select(elem[0]).append("table").attr('class','legend');

            // create one row per segment.
            var tr = legend.append("tbody").selectAll("tr").data(data).enter().append("tr");

            // create the first column for each segment.
            tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
                .attr("width", '16').attr("height", '16')
                .attr("fill",function(d, i){ return color(i) });

            // create the second column for each segment.
            tr.append("td").text(function(d){ return d.label;});

            // create the third column for each segment.
            tr.append("td").attr("class",'legendFreq')
                .text(function(d){ return d.value;});



        });

    },

    update_join_resign_trends: function(){
        var elem = this.$('.join_resign_trend');
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
        '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);
        rpc.query({
            model: "hr.employee",
            method: "join_resign_trends",
        }).then(function (data) {
            data.forEach(function(d) {
              d.values.forEach(function(d) {
                d.l_month = d.l_month;
                d.count = +d.count;
              });
            });
            var margin = {top: 30, right: 10, bottom: 30, left: 30},
                width = 400 - margin.left - margin.right,
                height = 250 - margin.top - margin.bottom;

            // Set the ranges
            var x = d3.scale.ordinal()
                .rangeRoundBands([0, width], 1);

            var y = d3.scale.linear()
                .range([height, 0]);

            // Define the axes
            var xAxis = d3.svg.axis().scale(x)
                .orient("bottom");

            var yAxis = d3.svg.axis().scale(y)
                .orient("left").ticks(5);

            x.domain(data[0].values.map(function(d) { return d.l_month; }));
            y.domain([0, d3.max(data[0].values, d => d.count)])

            var svg = d3.select(elem[0]).append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

            // Add the X Axis
            svg.append("g")
                .attr("class", "x axis")
                .attr("transform", "translate(0," + height + ")")
                .call(xAxis);

            // Add the Y Axis
            svg.append("g")
                .attr("class", "y axis")
                .call(yAxis);


            var line = d3.svg.line()
                .x(function(d) {return x(d.l_month); })
                .y(function(d) {return y(d.count); });

            let lines = svg.append('g')
              .attr('class', 'lines');

            lines.selectAll('.line-group')
                .data(data).enter()
                .append('g')
                .attr('class', 'line-group')
                .append('path')
                .attr('class', 'line')
                .attr('d', function(d) { return line(d.values); })
                .style('stroke', (d, i) => color(i));

            lines.selectAll("circle-group")
                .data(data).enter()
                .append("g")
                .selectAll("circle")
                .data(function(d) { return d.values;}).enter()
                .append("g")
                .attr("class", "circle")
                .append("circle")
                .attr("cx", function(d) { return x(d.l_month)})
                .attr("cy", function(d) { return y(d.count)})
                .attr("r", 3);

            var legend = d3.select(elem[0]).append("div").attr('class','legend');

            var tr = legend.selectAll("div").data(data).enter().append("div");

            tr.append("span").attr('class','legend_col').append("svg").attr("width", '16').attr("height", '16').append("rect")
                .attr("width", '16').attr("height", '16')
                .attr("fill",function(d, i){ return color(i) });

            tr.append("span").attr('class','legend_col').text(function(d){ return d.name;});
        });
    },

    update_monthly_attrition: function(){

        var elem = this.$('.attrition_rate');
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
        '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);
        rpc.query({
            model: "hr.employee",
            method: "get_attrition_rate",
        }).then(function (data) {
            var margin = {top: 30, right: 20, bottom: 30, left: 80},
                width = 500 - margin.left - margin.right,
                height = 250 - margin.top - margin.bottom;

            // Set the ranges
            var x = d3.scale.ordinal()
                .rangeRoundBands([0, width], 1);

            var y = d3.scale.linear()
                .range([height, 0]);

            // Define the axes
            var xAxis = d3.svg.axis().scale(x)
                .orient("bottom");

            var yAxis = d3.svg.axis().scale(y)
                .orient("left").ticks(5);

            var valueline = d3.svg.line()
                .x(function(d) { return x(d.month); })
                .y(function(d) { return y(d.attrition_rate); });


            var svg = d3.select(elem[0]).append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

            x.domain(data.map(function(d) { return d.month; }));
            y.domain([0, d3.max(data, function(d) { return d.attrition_rate; })]);

            // Add the X Axis
            svg.append("g")
                .attr("class", "x axis")
                .attr("transform", "translate(0," + height + ")")
                .call(xAxis);

            // Add the Y Axis
            svg.append("g")
                .attr("class", "y axis")
                .call(yAxis);

            svg.append("path")
                .attr("class", "line")
                .attr("d", valueline(data));

            // Add the scatterplot
            svg.selectAll("dot")
                .data(data)
                .enter().append("circle")
                .attr("r", 3)
                .attr("cx", function(d) { return x(d.month); })
                .attr("cy", function(d) { return y(d.attrition_rate); })
                .on("mouseover", function() { tooltip.style("display", null);
                    d3.select(this).transition().duration(500).ease("elastic").attr('r', 3 * 2)
                 })
                .on("mouseout", function() { tooltip.style("display", "none");
                    d3.select(this).transition().duration(500).ease("in-out").attr('r', 3)
                })
                .on("mousemove", function(d) {
                    var xPosition = d3.mouse(this)[0] - 15;
                    var yPosition = d3.mouse(this)[1] - 25;
                    tooltip.attr("transform", "translate(" + xPosition + "," + yPosition + ")");
                    tooltip.select("text").text(d.attrition_rate);
                });

            var tooltip = svg.append("g")
                  .attr("class", "tooltip")
                  .style("display", "none");

                tooltip.append("rect")
                  .attr("width", 30)
                  .attr("height", 20)
                  .attr("fill", "black")
                  .style("opacity", 0.5);

                tooltip.append("text")
                  .attr("x", 15)
                  .attr("dy", "1.2em")
                  .style("text-anchor", "middle")
                  .attr("font-size", "12px")
                  .attr("font-weight", "bold");

        });
    },

    update_leave_trend: function(){
        var self = this;
        rpc.query({
            model: "hr.employee",
            method: "employee_leave_trend",
        }).then(function (data) {
            var elem = self.$('.leave_trend');
            var margin = {top: 30, right: 20, bottom: 30, left: 80},
                width = 500 - margin.left - margin.right,
                height = 250 - margin.top - margin.bottom;

            // Set the ranges
            var x = d3.scale.ordinal()
                .rangeRoundBands([0, width], 1);

            var y = d3.scale.linear()
                .range([height, 0]);

            // Define the axes
            var xAxis = d3.svg.axis().scale(x)
                .orient("bottom");

            var yAxis = d3.svg.axis().scale(y)
                .orient("left").ticks(5);

            var valueline = d3.svg.line()
                .x(function(d) { return x(d.l_month); })
                .y(function(d) { return y(d.leave); });


            var svg = d3.select(elem[0]).append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

            x.domain(data.map(function(d) { return d.l_month; }));
            y.domain([0, d3.max(data, function(d) { return d.leave; })]);

            // Add the X Axis
            svg.append("g")
                .attr("class", "x axis")
                .attr("transform", "translate(0," + height + ")")
                .call(xAxis);

            // Add the Y Axis
            svg.append("g")
                .attr("class", "y axis")
                .call(yAxis);

            svg.append("path")
                .attr("class", "line")
                .attr("d", valueline(data));

            // Add the scatterplot
            svg.selectAll("dot")
                .data(data)
                .enter().append("circle")
                .attr("r", 3)
                .attr("cx", function(d) { return x(d.l_month); })
                .attr("cy", function(d) { return y(d.leave); })
//                .on('mouseover', function() { d3.select(this).transition().duration(500).ease("elastic").attr('r', 3 * 2) })
//                .on('mouseout', function() { d3.select(this).transition().duration(500).ease("in-out").attr('r', 3) });
                .on("mouseover", function() { tooltip.style("display", null);
                    d3.select(this).transition().duration(500).ease("elastic").attr('r', 3 * 2)
                 })
                .on("mouseout", function() { tooltip.style("display", "none");
                    d3.select(this).transition().duration(500).ease("in-out").attr('r', 3)
                })
                .on("mousemove", function(d) {
                    var xPosition = d3.mouse(this)[0] - 15;
                    var yPosition = d3.mouse(this)[1] - 25;
                    tooltip.attr("transform", "translate(" + xPosition + "," + yPosition + ")");
                    tooltip.select("text").text(d.leave);
                });

            var tooltip = svg.append("g")
                  .attr("class", "tooltip")
                  .style("display", "none");

                tooltip.append("rect")
                  .attr("width", 30)
                  .attr("height", 20)
                  .attr("fill", "black")
                  .style("opacity", 0.5);

                tooltip.append("text")
                  .attr("x", 15)
                  .attr("dy", "1.2em")
                  .style("text-anchor", "middle")
                  .attr("font-size", "12px")
                  .attr("font-weight", "bold");

        });
    },

    render_leave_graph:function(){

        var self = this;
//        var color = d3.scale.category10();
        var colors = ['#70cac1', '#659d4e', '#208cc2', '#4d6cb1', '#584999', '#8e559e', '#cf3650', '#f65337', '#fe7139',
        '#ffa433', '#ffc25b', '#f8e54b'];
        var color = d3.scale.ordinal().range(colors);
        rpc.query({
                model: "hr.employee",
                method: "get_department_leave",
            }).then(function (data) {
                var fData = data[0];
                var dept = data[1];
                var id = self.$('.leave_graph')[0];
                var barColor = '#ff618a';
                // compute total for each state.
                fData.forEach(function(d){
                    var total = 0;
                    for (var dpt in dept){
                        total += d.leave[dept[dpt]];
                    }
                d.total=total;
                });

                // function to handle histogram.
                function histoGram(fD){
                    var hG={},    hGDim = {t: 60, r: 0, b: 30, l: 0};
                    hGDim.w = 350 - hGDim.l - hGDim.r,
                    hGDim.h = 200 - hGDim.t - hGDim.b;

                    //create svg for histogram.
                    var hGsvg = d3.select(id).append("svg")
                        .attr("width", hGDim.w + hGDim.l + hGDim.r)
                        .attr("height", hGDim.h + hGDim.t + hGDim.b).append("g")
                        .attr("transform", "translate(" + hGDim.l + "," + hGDim.t + ")");

                    // create function for x-axis mapping.
                    var x = d3.scale.ordinal().rangeRoundBands([0, hGDim.w], 0.1)
                            .domain(fD.map(function(d) { return d[0]; }));

                    // Add x-axis to the histogram svg.
                    hGsvg.append("g").attr("class", "x axis")
                        .attr("transform", "translate(0," + hGDim.h + ")")
                        .call(d3.svg.axis().scale(x).orient("bottom"));

                    // Create function for y-axis map.
                    var y = d3.scale.linear().range([hGDim.h, 0])
                            .domain([0, d3.max(fD, function(d) { return d[1]; })]);

                    // Create bars for histogram to contain rectangles and freq labels.
                    var bars = hGsvg.selectAll(".bar").data(fD).enter()
                            .append("g").attr("class", "bar");

                    //create the rectangles.
                    bars.append("rect")
                        .attr("x", function(d) { return x(d[0]); })
                        .attr("y", function(d) { return y(d[1]); })
                        .attr("width", x.rangeBand())
                        .attr("height", function(d) { return hGDim.h - y(d[1]); })
                        .attr('fill',barColor)
                        .on("mouseover",mouseover)// mouseover is defined below.
                        .on("mouseout",mouseout);// mouseout is defined below.

                    //Create the frequency labels above the rectangles.
                    bars.append("text").text(function(d){ return d3.format(",")(d[1])})
                        .attr("x", function(d) { return x(d[0])+x.rangeBand()/2; })
                        .attr("y", function(d) { return y(d[1])-5; })
                        .attr("text-anchor", "middle");

                    function mouseover(d){  // utility function to be called on mouseover.
                        // filter for selected state.
                        var st = fData.filter(function(s){ return s.l_month == d[0];})[0],
                            nD = d3.keys(st.leave).map(function(s){ return {type:s, leave:st.leave[s]};});

                        // call update functions of pie-chart and legend.
                        pC.update(nD);
                        leg.update(nD);
                    }

                    function mouseout(d){    // utility function to be called on mouseout.
                        // reset the pie-chart and legend.
                        pC.update(tF);
                        leg.update(tF);
                    }

                    // create function to update the bars. This will be used by pie-chart.
                    hG.update = function(nD, color){
                        // update the domain of the y-axis map to reflect change in frequencies.
                        y.domain([0, d3.max(nD, function(d) { return d[1]; })]);

                        // Attach the new data to the bars.
                        var bars = hGsvg.selectAll(".bar").data(nD);

                        // transition the height and color of rectangles.
                        bars.select("rect").transition().duration(500)
                            .attr("y", function(d) {return y(d[1]); })
                            .attr("height", function(d) { return hGDim.h - y(d[1]); })
                            .attr("fill", color);

                        // transition the frequency labels location and change value.
                        bars.select("text").transition().duration(500)
                            .text(function(d){ return d3.format(",")(d[1])})
                            .attr("y", function(d) {return y(d[1])-5; });
                    }
                    return hG;
                }

                // function to handle pieChart.
                function pieChart(pD){
                    var pC ={},    pieDim ={w:250, h: 250};
                    pieDim.r = Math.min(pieDim.w, pieDim.h) / 2;

                    // create svg for pie chart.
                    var piesvg = d3.select(id).append("svg")
                        .attr("width", pieDim.w).attr("height", pieDim.h).append("g")
                        .attr("transform", "translate("+pieDim.w/2+","+pieDim.h/2+")");

                    // create function to draw the arcs of the pie slices.
                    var arc = d3.svg.arc().outerRadius(pieDim.r - 10).innerRadius(0);

                    // create a function to compute the pie slice angles.
                    var pie = d3.layout.pie().sort(null).value(function(d) { return d.leave; });

                    // Draw the pie slices.
                    piesvg.selectAll("path").data(pie(pD)).enter().append("path").attr("d", arc)
                        .each(function(d) { this._current = d; })
                        .attr("fill", function(d, i){return color(i);})
                        .on("mouseover",mouseover).on("mouseout",mouseout);

                    // create function to update pie-chart. This will be used by histogram.
                    pC.update = function(nD){
                        piesvg.selectAll("path").data(pie(nD)).transition().duration(500)
                            .attrTween("d", arcTween);
                    }
                    // Utility function to be called on mouseover a pie slice.
                    function mouseover(d, i){
                        // call the update function of histogram with new data.
                        hG.update(fData.map(function(v){
                            return [v.l_month,v.leave[d.data.type]];}),color(i));
                    }
                    //Utility function to be called on mouseout a pie slice.
                    function mouseout(d){
                        // call the update function of histogram with all data.
                        hG.update(fData.map(function(v){
                            return [v.l_month,v.total];}), barColor);

                    }
                    // Animating the pie-slice requiring a custom function which specifies
                    // how the intermediate paths should be drawn.
                    function arcTween(a) {
                        var i = d3.interpolate(this._current, a);
                        this._current = i(0);
                        return function(t) { return arc(i(t));    };
                    }
                    return pC;
                }

                // function to handle legend.
                function legend(lD){
                    var leg = {};

                    // create table for legend.
                    var legend = d3.select(id).append("table").attr('class','legend');

                    // create one row per segment.
                    var tr = legend.append("tbody").selectAll("tr").data(lD).enter().append("tr");

                    // create the first column for each segment.
                    tr.append("td").append("svg").attr("width", '16').attr("height", '16').append("rect")
                        .attr("width", '16').attr("height", '16')
                        .attr("fill", function(d, i){return color(i);})

                    // create the second column for each segment.
                    tr.append("td").text(function(d){ return d.type;});

                    // create the third column for each segment.
                    tr.append("td").attr("class",'legendFreq')
                        .text(function(d){ return d.l_month;});

                    // create the fourth column for each segment.
                    tr.append("td").attr("class",'legendPerc')
                        .text(function(d){ return getLegend(d,lD);});

                    // Utility function to be used to update the legend.
                    leg.update = function(nD){
                        // update the data attached to the row elements.
                        var l = legend.select("tbody").selectAll("tr").data(nD);

                        // update the frequencies.
                        l.select(".legendFreq").text(function(d){ return d3.format(",")(d.leave);});

                        // update the percentage column.
                        l.select(".legendPerc").text(function(d){ return getLegend(d,nD);});
                    }

                    function getLegend(d,aD){ // Utility function to compute percentage.
                        var perc = (d.leave/d3.sum(aD.map(function(v){ return v.leave; })));
                        if (isNaN(perc)){
                            return d3.format("%")(0);
                            }
                        else{
                            return d3.format("%")(d.leave/d3.sum(aD.map(function(v){ return v.leave; })));
                            }
                    }

                    return leg;
                }
                // calculate total frequency by segment for all state.
                var tF = dept.map(function(d){
                    return {type:d, leave: d3.sum(fData.map(function(t){ return t.leave[d];}))};
                });

                // calculate total frequency by state for all segment.
                var sF = fData.map(function(d){return [d.l_month,d.total];});

                var hG = histoGram(sF), // create the histogram.
                    pC = pieChart(tF), // create the pie-chart.
                    leg= legend(tF);  // create the legend.
        });
    },


   });

    core.action_registry.add('hr_dashboard', HrDashboard);

return HrDashboard;

});
