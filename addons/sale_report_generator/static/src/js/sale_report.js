/** @odoo-module **/
import AbstractAction from "web.AbstractAction";
import core from 'web.core';
import rpc from 'web.rpc';
const QWeb = core.qweb;
import { _t } from "web.core";
var datepicker = require('web.datepicker');
import time from "web.time";
import framework from 'web.framework';
import session from 'web.session';

const SaleReport = AbstractAction.extend({
    template: 'SaleReport',
    events: {
        'click #apply_filter': 'apply_filter',
        'click #pdf': 'print_pdf',
        'click #xlsx': 'print_xlsx',
        'click .view_sale_order': 'button_view_order',
        'mousedown div.input-group.date[data-target-input="nearest"]': '_onCalendarIconClick',
    },

    init: function(parent, action) {
        this._super(parent, action);
        this.report_lines = action.report_lines;
        this.wizard_id = action.context.wizard | null;
    },
    start: function() {
        var self = this;
        self.initial_render = true;

        rpc.query({
            model: 'sales.report',
            method: 'create',
            args: [{
            }]
        }).then(function(res) {
            self.wizard_id = res;
            self.load_data(self.initial_render);
            self.apply_filter();
        })
    },
//Calendar Icon onclick to get Calendar
    _onCalendarIconClick: function(ev) {
        var $calendarInputGroup = $(ev.currentTarget);
        var calendarOptions = {
            minDate: moment({
                y: 1000
            }),
            maxDate: moment().add(200, 'y'),
            calendarWeeks: true,
            defaultDate: moment().format(),
            sideBySide: true,
            buttons: {
                showClear: true,
                showClose: true,
                showToday: true,
            },
            icons: {
                date: 'fa fa-calendar',
            },
            locale: moment.locale(),
            format: time.getLangDateFormat(),
            widgetParent: 'body',
            allowInputToggle: true,
        };
        $calendarInputGroup.datetimepicker(calendarOptions);
    },

//This function call an rpc call to the model sales.report & function sale_report with args wizard_id
    load_data: function(initial_render = true) {
        var self = this;
        self._rpc({
            model: 'sales.report',
            method: 'sale_report',
            args: [
                [this.wizard_id]
            ],
        }).then(function(datas) {
            if (initial_render) {
                self.$('.filter_view_sr').html(QWeb.render('saleFilterView', {
                    filter_data: datas['filters'],
                }));
                self.$el.find('.report_type').select2({
                    placeholder: ' Report Type...',
                });
            }

            if (datas['orders'])
                self.$('.table_view_sr').html(QWeb.render('SaleOrderTable', {
                    filter: datas['filters'],
                    order: datas['orders'],
                    report_lines: datas['report_lines'],
                    main_lines: datas['report_main_line']
                }));
        })
    },
//PDF PRINT
    print_pdf: function(e) {
        e.preventDefault();
        var self = this;
        var action_title = self._title;
        self._rpc({
            model: 'sales.report',
            method: 'sale_report',
            args: [
                [self.wizard_id]
            ],
        }).then(function(data) {
            var action = {
                'type': 'ir.actions.report',
                'report_type': 'qweb-pdf',
                'report_name': 'sale_report_generator.sale_order_report',
                'report_file': 'sale_report_generator.sale_order_report',
                'data': {
                    'report_data': data
                },
                'context': {
                    'active_model': 'sales.report',
                    'landscape': 1,
                    'sale_order_report': true
                },
                'display_name': 'Sale Order',
            };
            return self.do_action(action);
        });
    },
    //Print XLSX
    print_xlsx: function() {
            var self = this;
        self._rpc({
            model: 'sales.report',
            method: 'sale_report',
            args: [
                [self.wizard_id]
            ],
        }).then(function(data) {
            var action = {
                'data': {
                    'model': 'sales.report',
                    'options': JSON.stringify(data['orders']),
                    'output_format': 'xlsx',
                    'report_data': JSON.stringify(data['report_lines']),
                    'report_name': 'Sale Report',
                    'dfr_data': JSON.stringify(data),
                },
            };
              self.downloadXlsx(action);
        });
    },
//Download XLSX
    downloadXlsx: function (action){
    framework.blockUI();
        session.get_file({
            url: '/sale_dynamic_xlsx_reports',
            data: action.data,
            complete: framework.unblockUI,
            error: (error) => this.call('crash_manager', 'rpc_error', error),
        });
    },
//Corresponding SaleOrder Tree,Form View
    button_view_order: function(event) {
        event.preventDefault();
        var self = this;
        var context = {};
        this.do_action({
            name: _t("Sale Order"),
            type: 'ir.actions.act_window',
            res_model: 'sale.order',
            view_type: 'form',
            domain: [
                    ['id', '=', $(event.target).closest('.view_sale_order').attr('id')]
            ],
            views: [
                [false, 'list'],
                [false, 'form']
            ],
            target: 'current'
        });
    },
    //Filter Function
    apply_filter: function() {
        var self = this;
        self.initial_render = false;
        var filter_data_selected = {};

        if (this.$el.find('.datetimepicker-input[name="date_from"]').val()) {
            filter_data_selected.date_from = moment(this.$el.find('.datetimepicker-input[name="date_from"]').val(), time.getLangDateFormat()).locale('en').format('YYYY-MM-DD');
        }
        if (this.$el.find('.datetimepicker-input[name="date_to"]').val()) {
            filter_data_selected.date_to = moment(this.$el.find('.datetimepicker-input[name="date_to"]').val(), time.getLangDateFormat()).locale('en').format('YYYY-MM-DD');
        }
        if ($(".report_type").length) {
            var report_res = document.getElementById("report_res")
            filter_data_selected.report_type = $(".report_type")[1].value
            report_res.value = $(".report_type")[1].value
            report_res.innerHTML = report_res.value;
            if ($(".report_type")[1].value == "") {
                report_res.innerHTML = "report_by_order";
            }
        }
        rpc.query({
            model: 'sales.report',
            method: 'write',
            args: [
                self.wizard_id, filter_data_selected
            ],
        }).then(function(res) {
            self.initial_render = false;
            self.load_data(self.initial_render);
        });
    },
});
core.action_registry.add("s_r", SaleReport);
return SaleReport;
