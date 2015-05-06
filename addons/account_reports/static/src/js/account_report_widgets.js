odoo.define('account.ReportWidget', function (require) {
'use strict';

var core = require('web.core');
var Widget = require('web.Widget');
var formats = require('web.formats');
var Model = require('web.Model');
var Session = require('web.session');
var time = require('web.time');

var QWeb = core.qweb;

var ReportWidget = Widget.extend({
    events: {
        'click .fa-pencil-square': 'clickPencil',
        'click .fa-pencil': 'clickPencil',
        'click .oe-account-foldable': 'fold',
        'click .oe-account-unfoldable': 'unfold',
        'click .saveFootNote': 'saveFootNote',
        'click span.aml': 'displayMoveLine',
        'click .fa-trash-o': 'rmContent',
        'click .closeSummary': 'rmContent',
        'click .oe-account-saved-summary > span': 'editSummary',
        "change *[name='date_filter']": 'onChangeDateFilter',
        "change *[name='date_filter_cmp']": 'onChangeCmpDateFilter',
        "change *[name='date_to']": 'onChangeCmpDateFilter',
        "change *[name='date_from']": 'onChangeCmpDateFilter',
        "change *[name='comparison']": 'onChangeComparison',
        "click input[name='summary']": 'onClickSummary',
        "click button.saveSummary": 'saveSummary',
        'click button.saveContent': 'saveContent',
        'click button#saveFootNote': 'saveFootNote',
        'click .oe-account-add-footnote': 'footnoteFromDropdown',
        'click .oe-account-to-graph': 'displayMoveLinesByAccountGraph',
    },
    saveFootNote: function(e) {
        self = this;
        var report_name = $(e.target).parents('#footnoteModal').siblings("div.page").attr("data-report-name");
        var context_id = $(e.target).parents('#footnoteModal').siblings("div.page").attr("data-context");
        var note = $("#note").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        var contextModel = new Model(this.context_by_reportname[report_name]);
        return contextModel.call('get_next_footnote_number', [[parseInt(context_id)]]).then(function (footNoteSeqNum) {
            self.curFootNoteTarget.parents('a').after(QWeb.render("supFootNoteSeqNum", {footNoteSeqNum: footNoteSeqNum}));
            return contextModel.query(['footnotes_manager_id'])
            .filter([['id', '=', context_id]]).first().then(function (context) {
                new Model('account.report.footnotes.manager').call('add_footnote', [[parseInt(context.footnotes_manager_id[0])], $("#type").val(), $("#target_id").val(), $("#column").val(), footNoteSeqNum, note]);
                $('#footnoteModal').find('form')[0].reset();
                $('#footnoteModal').modal('hide');
                $("div.page").append(QWeb.render("savedFootNote", {num: footNoteSeqNum, note: note}));
            });
        });
    },
    onKeyPress: function(e) {
        if ((e.which === 70) && (e.ctrlKey || e.metaKey) && e.shiftKey) { // Fold all
            $(".oe-account-foldable").trigger('click');
        }
        else if ((e.which === 229) && (e.ctrlKey || e.metaKey) && e.shiftKey) { // Unfold all
            $(".oe-account-unfoldable").trigger('click');
        }
    },
    start: function() {
        var self = this;
        QWeb.add_template("/account_reports/static/src/xml/account_report_financial_line.xml");
        this.$('[data-toggle="tooltip"]').tooltip()
        this.curFootNoteTarget;
        var res = this._super.apply(this, arguments);;
        var report_name = window.$("div.page").attr("data-report-name");
        Session.on('error', this, function(error){
            $('#report_error').modal('show');
        });
        var load_info = new Model('account.report.context.common').call('get_context_name_by_report_name').then(function (result) {
            self.context_by_reportname = JSON.parse(result);
        });
        $(window).on("keydown", this, this.onKeyPress);
        return $.when(res, load_info);
    },
    onClickSummary: function(e) {
        e.stopPropagation();
        $(e.target).parents("div.oe-account-summary").html(QWeb.render("editSummary"));
    },
    saveSummary: function(e) {
        e.stopPropagation();
        var report_name = $(e.target).parents("div.page").attr("data-report-name");
        var context_id = $(e.target).parents("div.page").attr("data-context");
        var summary = this.$("textarea[name='summary']").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        if (summary != '')
            $(e.target).parents("div.oe-account-summary").html(QWeb.render("savedSummary", {summary : summary}));
        else
            $(e.target).parents("div.oe-account-summary").html(QWeb.render("addSummary"));
        return new Model(this.context_by_reportname[report_name]).call('edit_summary', [[parseInt(context_id)], summary]);
    },
    onChangeComparison: function(e) {
        e.stopPropagation();
        var checkbox = $(e.target).is(":checked")
        if (checkbox) {
            this.$("label[for='date_filter_cmp']").parent().attr('style', '')
            this.$("label[for='date_to_cmp']").parent().parent().attr('style', '');
        }
        else {
            this.$("label[for='date_filter_cmp']").parent().attr('style', 'visibility: hidden');
            this.$("label[for='date_to_cmp']").parent().parent().attr('style', 'visibility: hidden');
        }
    },
    onChangeDateFilter: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var filter = $(e.target).val();
        var no_date_range = this.$("input[name='date_from']").length == 0;
        switch(filter) {
            case 'today':
                var dt = new Date();
                this.$("input[name='date_to']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dt));
                break;
            case 'last_month':
                var dt = new Date();
                dt.setDate(0); // Go to last day of last month (date to)
                this.$("input[name='date_to']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dt));
                if (!no_date_range) {
                    dt.setDate(1); // and then first day of last month (date from)
                    this.$("input[name='date_from']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dt));
                }
                break;
            case 'last_quarter':
                var dt = new Date();
                dt.setMonth((moment(dt).quarter() - 1) * 3); // Go to the first month of this quarter
                dt.setDate(0); // Then last day of last month (= last day of last quarter)
                this.$("input[name='date_to']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dt));
                if (!no_date_range) {
                    dt.setDate(1);
                    dt.setMonth(dt.getMonth() - 2);
                    this.$("input[name='date_from']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dt));
                }
                break;
            case 'last_year':
                var report_name = window.$("div.page").attr("data-report-name");
                var context_id = window.$("div.page").attr("data-context");
                new Model(this.context_by_reportname[report_name]).query(['company_id'])
                .filter([['id', '=', context_id]]).first().then(function (context) {
                    var today = new Date();
                    new Model('res.company').query(['fiscalyear_last_day', 'fiscalyear_last_month'])
                    .filter([['id', '=', context.company_id[0]]]).first().then(function (fy) {
                        if (today.getMonth() + 1 < fy.fiscalyear_last_month || (today.getMonth() + 1 == fy.fiscalyear_last_month && today.getDate() <= fy.fiscalyear_last_day)) {
                            var dt = new Date(today.getFullYear() - 1, fy.fiscalyear_last_month - 1, fy.fiscalyear_last_day, 12, 0, 0, 0)    
                        }
                        else {
                            var dt = new Date(today.getFullYear(), fy.fiscalyear_last_month - 1, fy.fiscalyear_last_day, 12, 0, 0, 0)
                        }
                        $("input[name='date_to']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dt));
                        if (!no_date_range) {
                            dt.setDate(dt.getDate() + 1);
                            dt.setFullYear(dt.getFullYear() - 1)
                            $("input[name='date_from']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dt));
                        }
                    });
                });
                break;
            case 'this_month':
                var dt = new Date();
                dt.setDate(1);
                this.$("input[name='date_from']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dt));
                dt.setMonth(dt.getMonth() + 1);
                dt.setDate(0);
                this.$("input[name='date_to']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dt));
                break;
            case 'this_year':
                var report_name = window.$("div.page").attr("data-report-name");
                var context_id = window.$("div.page").attr("data-context");
                new Model(this.context_by_reportname[report_name]).query(['company_id'])
                .filter([['id', '=', context_id]]).first().then(function (context) {
                    var today = new Date();
                    new Model('res.company').query(['fiscalyear_last_day', 'fiscalyear_last_month'])
                    .filter([['id', '=', context.company_id[0]]]).first().then(function (fy) {
                        if (today.getMonth() + 1 < fy.fiscalyear_last_month || (today.getMonth() + 1 == fy.fiscalyear_last_month && today.getDate() <= fy.fiscalyear_last_day)) {
                            var dt = new Date(today.getFullYear(), fy.fiscalyear_last_month - 1, fy.fiscalyear_last_day, 12, 0, 0, 0)
                        }
                        else {
                            var dt = new Date(today.getFullYear() + 1, fy.fiscalyear_last_month - 1, fy.fiscalyear_last_day, 12, 0, 0, 0)
                        }
                        $("input[name='date_to']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dt));
                        if (!no_date_range) {
                            dt.setDate(dt.getDate() + 1);
                            dt.setFullYear(dt.getFullYear() - 1);
                            $("input[name='date_from']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dt));
                        }
                    });
                });
                break;
        }
        if (filter == 'custom') {
            this.$(".custom-date").css("visibility", "visible");
        }
        else {
            this.$(".custom-date").css("visibility", "hidden");
        }
        this.onChangeCmpDateFilter();
    },
    onChangeCmpDateFilter: function() {
        if ($(".date_bank_reconciliation").length > 0) return;
        var date_filter = this.$("select[name='date_filter']").val();
        var cmp_filter = this.$("select[name='date_filter_cmp']").val();
        var no_date_range = this.$("input[name='date_from']").length == 0;
        if (cmp_filter == 'custom') {
            this.$(".custom-cmp").css("display", "inline");
            this.$("input[name='periods_number']").parent().attr('style', 'display: none');
            this.$("input[name='periods_number']").val(1);
        }
        else if (cmp_filter == 'no_comparison') {
            this.$(".custom-cmp").css("display", "none");
            this.$("input[name='periods_number']").parent().attr('style', 'display: none');
        }
        else {
            this.$(".custom-cmp").css("display", "none");
            this.$("input[name='periods_number']").parent().attr('style', '');
            var dtTo = this.$("input[name='date_to']").val();
            dtTo = moment(dtTo).toDate();
            if (!no_date_range) {
                var dtFrom = this.$("input[name='date_from']").val();
                dtFrom = formats.parse_value(dtFrom, {type:'date'})
                dtFrom = moment(dtFrom).toDate();
            }   
            if (cmp_filter == 'previous_period') {
                if (date_filter.search("quarter") > -1) {
                    var month = dtTo.getMonth()
                    dtTo.setMonth(dtTo.getMonth() - 2);
                    dtTo.setDate(0);
                    if (dtTo.getMonth() == month - 2) {
                        dtTo.setDate(0);
                    }
                    if (!no_date_range) {
                        dtFrom.setMonth(dtFrom.getMonth() - 3);
                    }
                }
                else if (date_filter.search("year") > -1) {
                    dtTo.setFullYear(dtTo.getFullYear() - 1);
                    if (!no_date_range) {
                        dtFrom.setFullYear(dtFrom.getFullYear() - 1);
                    }
                }
                else if (date_filter.search("month") > -1) {
                    dtTo.setDate(0);
                    if (!no_date_range) {
                        dtFrom.setMonth(dtFrom.getMonth() - 1);
                    }
                }
                else if (no_date_range) {
                    var month = dtTo.getMonth()
                    dtTo.setMonth(month - 1);
                    if (dtTo.getMonth() == month) {
                        dtTo.setDate(0);
                    }
                }
                else {
                    var diff = dtTo.getTime() - dtFrom.getTime();
                    dtTo = dtFrom;
                    dtTo.setDate(dtFrom.getDate() - 1);
                    dtFrom = new Date(dtTo.getTime() - diff);
                }                        
            }
            else {
                dtTo.setFullYear(dtTo.getFullYear() - 1);
                if (!no_date_range) {
                    dtFrom.setFullYear(dtFrom.getFullYear() - 1);
                }
            }
            if (!no_date_range) {
                this.$("input[name='date_from_cmp']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dtFrom));
            }
            this.$("input[name='date_to_cmp']").parents('.oe-account-datetimepicker').data("DateTimePicker").setValue(moment(dtTo));

        }
    },
    footnoteFromDropdown: function(e) {
        e.stopPropagation();
        e.preventDefault();
        self = this;
        self.curFootNoteTarget = $(e.target).parents("div.dropdown").find("span.account_id");
        var type = $(e.target).parents('tr').data('type');
        var target_id = $(e.target).parents('tr').data('id');
        var column = $(e.target).parents('td').index();
        $("#footnoteModal #type").val(type);
        $("#footnoteModal #target_id").val(target_id);
        $("#footnoteModal #column").val(column);
        $('#footnoteModal').on('hidden.bs.modal', function (e) {
            $(this).find('form')[0].reset();
        });
        $('#footnoteModal').modal('show');
    },
    editSummary: function(e) {
        e.stopPropagation();
        e.preventDefault;
        var $el = $(e.target);
        var height = Math.max($el.height(), 100);
        var text = $el.html().replace(/\s+/g, ' ').replace(/\r?\n/g, '').replace(/<br>/g, '\n').replace(/(\n\s*)+$/g, '');
        var par = $el.parents("div.oe-account-summary")
        $el.parents("div.oe-account-summary").html(QWeb.render("editSummary", {summary: text}));
        par.find("textarea").height(height);
    },
    clickPencil: function(e) {
        e.stopPropagation();
        e.preventDefault();
        self = this;
        if ($(e.target).parent().is('.oe-account-next-action')) {
            self.setNextAction(e);
        }
        else if ($(e.target).parents("div.oe-account-summary, p.footnote").length > 0) {
            var num = 0;
            if ($(e.target).parent().parent().is("p.footnote")) {
                $(e.target).parent().parent().attr('class', 'footnoteEdit')
                var $el = $(e.target).parent().parent().find('span.text');
                var text = $el.html().replace(/\s+/g, ' ').replace(/\r?\n/g, '').replace(/<br>/g, '\n').replace(/(\n\s*)+$/g, '');
                text = text.split('.');
                var num = text[0];
                text = text[1];
                $el.html(QWeb.render("editContent", {num: num, text: text}));
            }
            else {
                var $el = $(e.target).parents('div.oe-account-saved-summary').children('span');
                var height = $el.height();
                var text = $el.html().replace(/\s+/g, ' ').replace(/\r?\n/g, '').replace(/<br>/g, '\n').replace(/(\n\s*)+$/g, '');
                var par = $el.parent()
                $el.replaceWith(QWeb.render("editContent", {num: 0, text: text}));
                par.find("textarea").height(height);
            }
        }
        else if ($(e.target).parent().parent().find("sup").length == 0) {
            self.curFootNoteTarget = $(e.target).parent().parent();
            var type = $(e.target).parents('tr').data('type');
            var target_id = $(e.target).parents('tr').data('id');
            var column = $(e.target).parents('td').index();
            $("#footnoteModal #type").val(type);
            $("#footnoteModal #target_id").val(target_id);
            $("#footnoteModal #column").val(column);
            $('#footnoteModal').on('hidden.bs.modal', function (e) {
                $(this).find('form')[0].reset();
            });
            $('#footnoteModal').modal('show');
        }
    },
    saveContent: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var report_name = $(e.target).parents("div.page").attr("data-report-name");
        var context_id = $(e.target).parents("div.page").attr("data-context");
        var text = $(e.target).siblings('textarea').val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        var footNoteSeqNum = $(e.target).parents('p.footnoteEdit').text().split('.')[0];
        if ($(e.target).parents("p.footnoteEdit").length > 0) {
            $(e.target).parents("p.footnoteEdit").attr('class', 'footnote')
            $(e.target).siblings('textarea').replaceWith(text);
            new Model(this.context_by_reportname[report_name]).query(['footnotes_manager_id'])
            .filter([['id', '=', context_id]]).first().then(function (context) {
                new Model('account.report.footnotes.manager').call('edit_footnote', [[parseInt(context.footnotes_manager_id[0])], parseInt(footNoteSeqNum), text]);
            });
        }
        else {
            if (text != '')
                $(e.target).parents("div.oe-account-summary").html(QWeb.render("savedSummary", {summary : text}));
            else
                $(e.target).parents("div.oe-account-summary").html(QWeb.render("addSummary"));
            new Model(this.context_by_reportname[report_name]).call('edit_summary', [[parseInt(context_id)], text]);
        }
        $(e.target).remove();
    },
    rmContent: function(e) {
        e.stopPropagation();
        e.preventDefault();
        if ($(e.target).parents("div.oe-account-summary").length > 0) {
            var report_name = $(e.target).parents("div.page").attr("data-report-name");
            var context_id = $(e.target).parents("div.page").attr("data-context");
            $(e.target).parent().parent().replaceWith(QWeb.render("addSummary"));
            new Model(this.context_by_reportname[report_name]).call('edit_summary', [[parseInt(context_id)], '']);
        }
        else {
            var num = $(e.target).parent().parent().text().split('.')[0].replace(/ /g,'').replace(/\r?\n/g,'');
            this.$("sup b a:contains('" + num + "')").parents('sup').remove();
            $(e.target).parent().parent().remove();
            var report_name = window.$("div.page").attr("data-report-name");
            var context_id = window.$("div.page").attr("data-context");
            new Model(this.context_by_reportname[report_name]).query(['footnotes_manager_id'])
            .filter([['id', '=', context_id]]).first().then(function (context) {
                new Model('account.report.footnotes.manager').call('remove_footnote', [[parseInt(context.footnotes_manager_id[0])], parseInt(num)]);
            });
        }
    },
    fold: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var report_name = $(e.target).parents("div.page").attr("data-report-name");
        var context_id = $(e.target).parents("div.page").attr("data-context");
        var el;
        var $el;
        var $nextEls = $(e.target).parents('tr').nextAll();
        for (el in $nextEls) {
            $el = $($nextEls[el]).find("td span.oe-account-domain-line-1, td span.oe-account-domain-line-2, td span.oe-account-domain-line-3");
            if ($el.length == 0)
                break;
            else {
                $($el[0]).parents("tr").hide();
            }
        }
        var active_id = $(e.target).parents('tr').find('td.oe-account-foldable').data('id');
        $(e.target).parents('tr').find('td.oe-account-foldable').attr('class', 'oe-account-unfoldable ' + active_id)
        $(e.target).parents('tr').find('span.oe-account-foldable').replaceWith(QWeb.render("unfoldable", {lineId: active_id}));
        return new Model(this.context_by_reportname[report_name]).call('remove_line', [[parseInt(context_id)], parseInt(active_id)]);
    },
    unfold: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var self = this;
        var report_name = window.$("div.page").attr("data-report-name");
        var context_id = window.$("div.page").attr("data-context");
        var active_id = $(e.target).parents('tr').find('td.oe-account-unfoldable').data('id');
        var contextObj = new Model(this.context_by_reportname[report_name]);
        return contextObj.call('add_line', [[parseInt(context_id)], parseInt(active_id)]).then(function (result) {
            var el;
            var $el;
            var $nextEls = $(e.target).parents('tr').nextAll();
            var isLoaded = false;
            for (el in $nextEls) {
                $el = $($nextEls[el]).find("td span.oe-account-domain-line-1, td span.oe-account-domain-line-2, td span.oe-account-domain-line-3");
                if ($el.length == 0)
                    break;
                else {
                    $($el[0]).parents("tr").show();
                    isLoaded = true;
                }
            }
            if (!isLoaded) {
                var $cursor = $(e.target).parents('tr');
                new Model('account.report.context.common').call('get_full_report_name_by_report_name', [report_name]).then(function (result) {
                    var reportObj = new Model(result);
                    var f = function (lines) {
                        new Model(self.context_by_reportname[report_name]).query(['all_entries', 'cash_basis'])
                        .filter([['id', '=', context_id]]).first().then(function (context) {
                            new Model(self.context_by_reportname[report_name]).call('get_columns_types', [[parseInt(context_id)]]).then(function (types) {
                                var line;
                                lines.shift();
                                for (line in lines) {
                                    $cursor.after(QWeb.render("report_financial_line", {l: lines[line], context: context, types: types}));
                                    $cursor = $cursor.next();
                                }
                            });
                        });
                    };
                    if (report_name == 'financial_report') {
                        contextObj.query(['report_id'])
                        .filter([['id', '=', context_id]]).first().then(function (context) {
                            reportObj.call('get_lines', [[parseInt(context.report_id[0])], parseInt(context_id), parseInt(active_id)]).then(f);
                        });
                    }
                    else {
                        reportObj.call('get_lines', [parseInt(context_id), parseInt(active_id)]).then(f);
                    }
                });
            }
            $(e.target).parents('tr').find('td.oe-account-unfoldable').attr('class', 'oe-account-foldable ' + active_id)
            $(e.target).parents('tr').find('span.oe-account-unfoldable').replaceWith(QWeb.render("foldable", {lineId: active_id}));
        });
    },
});

return ReportWidget;

});