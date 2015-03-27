openerp.account.ReportWidgets = openerp.Widget.extend({
    events: {
        'click .fa-pencil-square': 'clickPencil',
        'click .fa-pencil': 'clickPencil',
        'click .oe-account-foldable': 'fold',
        'click .oe-account-unfoldable': 'unfold',
        'click .saveFootNote': 'saveFootNote',
        'click .oe-account-to-amls': 'displayMoveLinesByAccount',
        'click span.user_type': 'displayMoveLinesByType',
        'click span.partner_id': 'displayFollowup',
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
        'click .oe-account-to-net': 'displayNetTaxLines',
        'click .oe-account-to-tax': 'displayTaxLines',
        'click .oe-account-to-bank-statement': 'display_bank_statement',
        'click .move_line_id': 'onClickAML',
        'click .to_invoice': 'displayInvoice',
        'click .to_payment': 'displayPayment',
    },
    saveFootNote: function(e) {
        self = this;
        var report_name = $(e.target).parents('#footnoteModal').siblings("div.page").attr("data-report-name");
        var context_id = $(e.target).parents('#footnoteModal').siblings("div.page").attr("data-context");
        var note = $("#note").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        var model = new openerp.Model('account.report.context.common');
        return model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            var contextModel = new openerp.Model(result);
            return contextModel.call('get_next_footnote_number', [[parseInt(context_id)]]).then(function (footNoteSeqNum) {
                self.curFootNoteTarget.append(openerp.qweb.render("supFootNoteSeqNum", {footNoteSeqNum: footNoteSeqNum}));
                return contextModel.query(['footnotes_manager_id'])
                .filter([['id', '=', context_id]]).first().then(function (context) {
                    var managerModel = new openerp.Model('account.report.footnotes.manager');
                    managerModel.call('add_footnote', [[parseInt(context.footnotes_manager_id[0])], $("#type").val(), $("#target_id").val(), $("#column").val(), footNoteSeqNum, note]);
                    $('#footnoteModal').find('form')[0].reset();
                    $('#footnoteModal').modal('hide');
                    $("div.page").append(openerp.qweb.render("savedFootNote", {num: footNoteSeqNum, note: note}));
                });
            });
        });
    },
    start: function() {
        openerp.qweb.add_template("/account/static/src/xml/account_report_financial_line.xml");
        this.$('[data-toggle="tooltip"]').tooltip()
        this.curFootNoteTarget;
        var res = this._super();
        var report_name = window.$("div.page").attr("data-report-name");
        openerp.session.on('error', this, function(error){
            $('#report_error').modal('show');
        });
        var l10n = openerp.web._t.database.parameters;
        var $datetimepickers = this.$('.oe-account-datetimepicker');
        var options = {
            language : moment.locale(),
            format : openerp.web.normalize_format(l10n.date_format),
            icons: {
                date: "fa fa-calendar",
            },
            pickTime: false,
        }
        $("*[name='form']").submit(function () {
            $('.oe-account-datetimepicker input').each(function () {
                $(this).val(openerp.web.parse_value($(this).val(), {type: 'date'}));
            })
        })
        $datetimepickers.each(function () {
            $(this).datetimepicker(options);
            if($(this).data('default-value')) {
                $(this).data("DateTimePicker").setValue(moment($(this).data('default-value')));
            }
            delete options.linkFormat;
            delete options.linkField;
        })
        if(report_name != 'followup_report') {
            this.onChangeCmpDateFilter();
        }
        return res;
    },
    onClickSummary: function(e) {
        e.stopPropagation();
        $(e.target).parents("div.oe-account-summary").html(openerp.qweb.render("editSummary"));
    },
    saveSummary: function(e) {
        e.stopPropagation();
        var report_name = $(e.target).parents("div.page").attr("data-report-name");
        var context_id = $(e.target).parents("div.page").attr("data-context");
        var summary = this.$("textarea[name='summary']").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        if (summary != '')
            $(e.target).parents("div.oe-account-summary").html(openerp.qweb.render("savedSummary", {summary : summary}));
        else
            $(e.target).parents("div.oe-account-summary").html(openerp.qweb.render("addSummary"));
        var model = new openerp.Model('account.report.context.common');
        return model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            var contextModel = new openerp.Model(result);
            contextModel.call('edit_summary', [[parseInt(context_id)], summary]);
        });
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
                var commonContext = new openerp.Model('account.report.context.common');
                commonContext.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                    var contextObj = new openerp.Model(result);
                    contextObj.query(['company_id'])
                    .filter([['id', '=', context_id]]).first().then(function (context) {
                        var compObj = new openerp.Model('res.company');
                        var today = new Date();
                        compObj.query(['fiscalyear_last_day', 'fiscalyear_last_month'])
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
                var commonContext = new openerp.Model('account.report.context.common');
                commonContext.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                    var contextObj = new openerp.Model(result);
                    contextObj.query(['company_id'])
                    .filter([['id', '=', context_id]]).first().then(function (context) {
                        var compObj = new openerp.Model('res.company');
                        var today = new Date();
                        compObj.query(['fiscalyear_last_day', 'fiscalyear_last_month'])
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
                dtFrom = openerp.web.parse_value(dtFrom, {type:'date'})
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
        var report_name = $(e.target).parents("div.page").attr("data-report-name");
        var context_id = $(e.target).parents("div.page").attr("data-context");
        var model = new openerp.Model('account.report.context.common');
        return model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            self.curFootNoteTarget = $(e.target).parents("div.dropdown").find("span.account_id");
            var contextModel = new openerp.Model(result);
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
        });
    },
    editSummary: function(e) {
        e.stopPropagation();
        e.preventDefault;
        var $el = $(e.target);
        var height = Math.max($el.height(), 100);
        var text = $el.html().replace(/\s+/g, ' ').replace(/\r?\n/g, '').replace(/<br>/g, '\n').replace(/(\n\s*)+$/g, '');
        var par = $el.parents("div.oe-account-summary")
        $el.parents("div.oe-account-summary").html(openerp.qweb.render("editSummary", {summary: text}));
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
                $el.html(openerp.qweb.render("editContent", {num: num, text: text}));
            }
            else {
                var $el = $(e.target).parents('div.oe-account-saved-summary').children('span');
                var height = $el.height();
                var text = $el.html().replace(/\s+/g, ' ').replace(/\r?\n/g, '').replace(/<br>/g, '\n').replace(/(\n\s*)+$/g, '');
                var par = $el.parent()
                $el.replaceWith(openerp.qweb.render("editContent", {num: 0, text: text}));
                par.find("textarea").height(height);
            }
        }
        else if ($(e.target).parent().parent().find("sup").length == 0) {
            var report_name = $(e.target).parents("div.page").attr("data-report-name");
            var context_id = $(e.target).parents("div.page").attr("data-context");
            var model = new openerp.Model('account.report.context.common');
            return model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                self.curFootNoteTarget = $(e.target).parent().parent();
                var contextModel = new openerp.Model(result);
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
            });
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
            var model = new openerp.Model('account.report.context.common');
            model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                var contextModel = new openerp.Model(result);
                contextModel.query(['footnotes_manager_id'])
                .filter([['id', '=', context_id]]).first().then(function (context) {
                    var managerModel = new openerp.Model('account.report.footnotes.manager');
                    managerModel.call('edit_footnote', [[parseInt(context.footnotes_manager_id[0])], parseInt(footNoteSeqNum), text]);
                });
            });
        }
        else {
            if (text != '')
                $(e.target).parents("div.oe-account-summary").html(openerp.qweb.render("savedSummary", {summary : text}));
            else
                $(e.target).parents("div.oe-account-summary").html(openerp.qweb.render("addSummary"));
            var model = new openerp.Model('account.report.context.common');
            model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                var contextModel = new openerp.Model(result);
                contextModel.call('edit_summary', [[parseInt(context_id)], text]);
            });
        }
        $(e.target).remove();
    },
    rmContent: function(e) {
        e.stopPropagation();
        e.preventDefault();
        if ($(e.target).parents("div.oe-account-summary").length > 0) {
            var report_name = $(e.target).parents("div.page").attr("data-report-name");
            var context_id = $(e.target).parents("div.page").attr("data-context");
            $(e.target).parent().parent().replaceWith(openerp.qweb.render("addSummary"));
            var model = new openerp.Model('account.report.context.common');
            return model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                var contextModel = new openerp.Model(result);
                contextModel.call('edit_summary', [[parseInt(context_id)], '']);
            });
        }
        else {
            var num = $(e.target).parent().parent().text().split('.')[0].replace(/ /g,'').replace(/\r?\n/g,'');
            this.$("sup b a:contains('" + num + "')").remove();
            $(e.target).parent().parent().remove();
            var report_name = window.$("div.page").attr("data-report-name");
            var context_id = window.$("div.page").attr("data-context");
            var model = new openerp.Model('account.report.context.common');
            return model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                var contextModel = new openerp.Model(result);
                contextModel.query(['footnotes_manager_id'])
                .filter([['id', '=', context_id]]).first().then(function (context) {
                    var managerModel = new openerp.Model('account.report.footnotes.manager');
                    managerModel.call('remove_footnote', [[parseInt(context.footnotes_manager_id[0])], parseInt(num)]);
                });
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
            $el = $($nextEls[el]).find("td span.oe-account-domain-line");
            if ($el.length == 0)
                break;
            else {
                $($el[0]).parents("tr").hide();
            }
        }
        var active_id = $(e.target).parents('tr').find('td.oe-account-foldable').data('id');
        $(e.target).parents('tr').find('td.oe-account-foldable').attr('class', 'oe-account-unfoldable ' + active_id)
        $(e.target).parents('tr').find('span.oe-account-foldable').replaceWith(openerp.qweb.render("unfoldable", {lineId: active_id}));
        var model = new openerp.Model('account.report.context.common');
        return model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            var contextModel = new openerp.Model(result);
            return contextModel.call('remove_line', [[parseInt(context_id)], parseInt(active_id)]);
        });
    },
    unfold: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var report_name = window.$("div.page").attr("data-report-name");
        var context_id = window.$("div.page").attr("data-context");
        var active_id = $(e.target).parents('tr').find('td.oe-account-unfoldable').data('id');
        var commonContext = new openerp.Model('account.report.context.common');
        return commonContext.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            var contextObj = new openerp.Model(result);
            return contextObj.call('add_line', [[parseInt(context_id)], parseInt(active_id)]).then(function (result) {
                var el;
                var $el;
                var $nextEls = $(e.target).parents('tr').nextAll();
                var isLoaded = false;
                for (el in $nextEls) {
                    $el = $($nextEls[el]).find("td span.oe-account-domain-line");
                    if ($el.length == 0)
                        break;
                    else {
                        $($el[0]).parents("tr").show();
                        isLoaded = true;
                    }
                }
                if (!isLoaded) {
                    var $cursor = $(e.target).parents('tr');
                    commonContext.call('get_full_report_name_by_report_name', [report_name]).then(function (result) {
                        var reportObj = new openerp.Model(result);
                        var f = function (lines) {
                            var line;
                            lines.shift();
                            for (line in lines) {
                                $cursor.after(openerp.qweb.render("report_financial_line", {l: lines[line]}));
                                $cursor = $cursor.next();
                            }
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
                $(e.target).parents('tr').find('span.oe-account-unfoldable').replaceWith(openerp.qweb.render("foldable", {lineId: active_id}));
            });
        });
    },
    displayMoveLinesByAccount: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).parents("div.dropdown").find("span.account_id").data('id');
        var report_name = window.$("div.page").attr("data-report-name");
        var context_id = window.$("div.page").attr("data-context");
        var commonContext = new openerp.Model('account.report.context.common');
        return commonContext.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            var contextObj = new openerp.Model(result);
            return contextObj.query(['all_entries', 'cash_basis'])
            .filter([['id', '=', context_id]]).first().then(function (context) {
                var action = 'action_move_line_select'
                if (context.cash_basis) {
                    action = 'action_move_line_graph_cash_basis'
                }
                if (!context.all_entries) {
                    action += '_posted'
                }
                var model = new openerp.Model('ir.model.data');
                return model.call('get_object_reference', ['account', action]).then(function (result) {
                    window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
                });
            });
        });
    },
    displayMoveLinesByAccountGraph: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).parents("div.dropdown").find("span.account_id").data('id');
        var report_name = window.$("div.page").attr("data-report-name");
        var context_id = window.$("div.page").attr("data-context");
        var commonContext = new openerp.Model('account.report.context.common');
        return commonContext.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            var contextObj = new openerp.Model(result);
            return contextObj.query(['all_entries'])
            .filter([['id', '=', context_id]]).first().then(function (context) {
                var action = 'action_move_line_graph'
                if (!context.all_entries) {
                    action = 'action_move_line_graph_posted'
                }
                var model = new openerp.Model('ir.model.data');
                return model.call('get_object_reference', ['account', action]).then(function (result) {
                    window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
                });
            });
        });
    },
    displayMoveLinesByType: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).data('id');
        var model = new openerp.Model('ir.model.data');
        return model.call('get_object_reference', ['account', 'action_move_line_select_by_type']).then(function (result) {
            window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
        });
    },
    displayMoveLinesByPartner: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).data('id');
        var model = new openerp.Model('ir.model.data');
        return model.call('get_object_reference', ['account', 'action_move_line_select_by_partner']).then(function (result) {
            window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
        });
    },
    displayNetTaxLines: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).parents("div.dropdown").find("span.account_id").data('id');
        var report_name = window.$("div.page").attr("data-report-name");
        var context_id = window.$("div.page").attr("data-context");
        var commonContext = new openerp.Model('account.report.context.common');
        return commonContext.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            var contextObj = new openerp.Model(result);
            return contextObj.query(['all_entries'])
            .filter([['id', '=', context_id]]).first().then(function (context) {
                var action = 'act_account_tax_net'
                if (!context.all_entries) {
                    action = 'act_account_tax_net_posted'
                }
                var model = new openerp.Model('ir.model.data');
                return model.call('get_object_reference', ['account', action]).then(function (result) {
                    window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
                });
            });
        });
    },
    displayTaxLines: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).parents("div.dropdown").find("span.account_id").data('id');
        var report_name = window.$("div.page").attr("data-report-name");
        var context_id = window.$("div.page").attr("data-context");
        var commonContext = new openerp.Model('account.report.context.common');
        return commonContext.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            var contextObj = new openerp.Model(result);
            return contextObj.query(['all_entries'])
            .filter([['id', '=', context_id]]).first().then(function (context) {
                var action = 'act_account_tax_tax'
                if (!context.all_entries) {
                    action = 'act_account_tax_tax_posted'
                }
                var model = new openerp.Model('ir.model.data');
                return model.call('get_object_reference', ['account', action]).then(function (result) {
                    window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
                });
            });
        });
    },
    displayTax: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).data('id');
        window.open("/web?#id=" + active_id + "&view_type=form&model=account.tax", "_self");
    },
    display_bank_statement: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).data('id');
        window.open("/web?#id=" + active_id + "&view_type=form&model=account.bank.statement", "_self");
    },
    displayFollowup: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).data('id');
        window.open("/account/followup_report/" + active_id, "_self");
    },
    onClickAML: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).data('id');
        var model = new openerp.Model('account.move.line');
        return model.call('get_model_and_id', [[parseInt(active_id)]]).then(function (result) {
            window.open("/web?#id=" + result[1] + "&view_type=form&model=" + result[0], "_self");
        })
    },
    displayInvoice: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).parents("div.dropdown").find("span.unreconciled_aml").data('id');
        var model = new openerp.Model('account.move.line');
        return model.query(['invoice'])
        .filter([['id', '=', active_id]]).first().then(function (result) {
            window.open("/web#id=" + result.invoice[0] + "&view_type=form&model=account.invoice", "_self");
        });
    },
    displayPayment: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).parents("div.dropdown").find("span.unreconciled_aml").data('id');
        var model = new openerp.Model('account.move.line');
        return model.query(['statement_id'])
        .filter([['id', '=', active_id]]).first().then(function (result) {
            window.open("/web#id=" + result.statement_id[0] + "&view_type=form&model=account.bank.statement", "_self");
        });
    },
});
