openerp.account.ReportWidgets = openerp.Widget.extend({
    events: {
        'click .fa-pencil-square': 'clickPencil',
        'click .fa-pencil': 'clickPencil',
        'click .foldable': 'fold',
        'click .unfoldable': 'unfold',
        'click .saveFootNote': 'saveFootNote',
        'click .to_amls': 'displayMoveLinesByAccount',
        'click span.user_type': 'displayMoveLinesByType',
        'click span.partner_id': 'displayFollowup',
        'click span.aml': 'displayMoveLine',
        'mouseleave td': 'rmPencil',
        'mouseleave .footnote': 'rmPencil',
        'click .fa-trash-o': 'rmContent',
        'click .closeSummary': 'rmContent',
        'click .savedSummary > span': 'editSummary',
        "change *[name='date_filter']": 'onChangeDateFilter',
        "change *[name='date_filter_cmp']": 'onChangeCmpDateFilter',
        "change *[name='date_to']": 'onChangeCmpDateFilter',
        "change *[name='date_from']": 'onChangeCmpDateFilter',
        "change *[name='comparison']": 'onChangeComparison',
        "click input[name='summary']": 'onClickSummary',
        "click button.saveSummary": 'saveSummary',
        'click button.saveContent': 'saveContent',
        'click button#saveFootNote': 'saveFootNote',
        'click .add_footnote': 'footnoteFromDropdown',
        'click .to_graph': 'displayMoveLinesByAccountGraph',
        'click .to_net': 'displayNetTaxLines',
        'click .to_tax': 'displayTaxLines',
        'click .to_invoice': 'displayInvoice',
        'click .to_payment': 'displayPayment',
    },
    saveFootNote: function(e) {
        self = this;
        var report_name = $(e.target).parents('#footnoteModal').siblings("div.page").attr("class").split(/\s+/)[2];
        var context_id = $(e.target).parents('#footnoteModal').siblings("div.page").attr("class").split(/\s+/)[3];
        var note = $("#note").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        var model = new openerp.Model('account.report.context.common');
        model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            var contextModel = new openerp.Model(result);
            contextModel.call('get_next_footnote_number', [[parseInt(context_id)]]).then(function (footNoteSeqNum) {
                self.curFootNoteTarget.append(openerp.qweb.render("supFootNoteSeqNum", {footNoteSeqNum: footNoteSeqNum}));
                contextModel.call('add_footnote', [[parseInt(context_id)], $("#footnoteModal #type").val(), $("#footnoteModal #target_id").val(), $("#footnoteModal #column").val(), footNoteSeqNum, note]);
                $('#footnoteModal').find('form')[0].reset();
                $('#footnoteModal').modal('hide');
                $("div.page").append(openerp.qweb.render("savedFootNote", {num: footNoteSeqNum, note: note}));
            });
        });
    },
    start: function() {
        openerp.qweb.add_template("/account/static/src/xml/account_report_financial_line.xml");
        this.$('[data-toggle="tooltip"]').tooltip()
        this.curFootNoteTarget;
        var res = this._super();
        var report_name = window.$("div.page").attr("class").split(/\s+/)[2];
        if(report_name != 'followup_report') {
            this.onChangeCmpDateFilter();
        }
        return res;
    },
    onClickSummary: function(e) {
        e.stopPropagation();
        $(e.target).parents("div.summary").html(openerp.qweb.render("editSummary"));
    },
    saveSummary: function(e) {
        e.stopPropagation();
        var report_name = $(e.target).parents("div.page").attr("class").split(/\s+/)[2];
        var context_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
        var summary = this.$("textarea[name='summary']").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        if (summary != '')
            $(e.target).parents("div.summary").html(openerp.qweb.render("savedSummary", {summary : summary}));
        else
            $(e.target).parents("div.summary").html(openerp.qweb.render("addSummary"));
        var model = new openerp.Model('account.report.context.common');
        model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
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
                this.$("input[name='date_to']").val(dt.toISOString().substr(0, 10));
                break;
            case 'last_month':
                var dt = new Date();
                dt.setDate(0);
                this.$("input[name='date_to']").val(dt.toISOString().substr(0, 10)); 
                if (!no_date_range) {
                    dt.setDate(1);
                    this.$("input[name='date_from']").val(dt.toISOString().substr(0, 10)); 
                }
                break;
            case 'last_quarter':
                var dt = new Date();
                dt.setMonth((Math.floor((dt.getMonth())/3)) * 3);
                dt.setDate(0);
                this.$("input[name='date_to']").val(dt.toISOString().substr(0, 10));
                if (!no_date_range) {
                    dt.setDate(1);
                    dt.setMonth(dt.getMonth() - 2);
                    this.$("input[name='date_from']").val(dt.toISOString().substr(0, 10)); 
                }
                break;
            case 'last_year':
                var report_name = $(e.target).parents("div.page").attr("class").split(/\s+/)[2];
                var context_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
                var commonContext = new openerp.Model('account.report.context.common');
                commonContext.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                    var contextObj = new openerp.Model(result);
                    contextObj.query(['company_id'])
                    .filter([['id', '=', context_id]]).first().then(function (context) {
                        var fyObj = new openerp.Model('account.fiscalyear');
                        var today = new Date();
                        var today_last_year = today
                        today_last_year.setFullYear(today.getFullYear() - 1);
                        today_last_year = today_last_year.toISOString().substr(0, 10);
                        fyObj.query(['date_start', 'date_stop'])
                        .filter([['company_id', '=', context.company_id[1]], ['date_start', '<', today_last_year], ['date_stop', '>', today_last_year]]).all().then(function (fy) {
                            if (fy.length == 0) {
                                var dt = new Date();
                                dt.setMonth(0);
                                dt.setDate(0);
                                $("input[name='date_to']").val(dt.toISOString().substr(0, 10));
                                $(".form-group").prepend(openerp.qweb.render("fiscalYearAlert"));
                                if (!no_date_range) {
                                    dt.setDate(1);
                                    dt.setMonth(0);
                                    $("input[name='date_from']").val(dt.toISOString().substr(0, 10)); 
                                }
                            }
                            else {
                                fy = fy[0];
                                $("input[name='date_to']").val(fy.date_stop);
                                if (!no_date_range) {
                                    $("input[name='date_from']").val(fy.date_start); 
                                }
                            }
                        });

                    });
                    
                });
                break;
            case 'this_month':
                var dt = new Date();
                dt.setDate(1);
                this.$("input[name='date_from']").val(dt.toISOString().substr(0, 10)); 
                dt.setMonth(dt.getMonth() + 1);
                dt.setDate(0);
                this.$("input[name='date_to']").val(dt.toISOString().substr(0, 10)); 
                break;
            case 'this_year':
                var report_name = $(e.target).parents("div.page").attr("class").split(/\s+/)[2];
                var context_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
                var commonContext = new openerp.Model('account.report.context.common');
                commonContext.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                    var contextObj = new openerp.Model(result);
                    contextObj.query(['company_id'])
                    .filter([['id', '=', context_id]]).first().then(function (context) {
                        var fyObj = new openerp.Model('account.fiscalyear');
                        var today = new Date();
                        today = today.toISOString().substr(0, 10);
                        fyObj.query(['date_start', 'date_stop'])
                        .filter([['company_id', '=', context.company_id[1]], ['date_start', '<', today], ['date_stop', '>', today]]).all().then(function (fy) {
                            if (fy.length == 0) {
                                var dt = new Date();
                                dt.setDate(1);
                                dt.setMonth(0);
                                $("input[name='date_from']").val(dt.toISOString().substr(0, 10)); 
                                dt.setDate(31);
                                dt.setMonth(11);
                                $("input[name='date_to']").val(dt.toISOString().substr(0, 10)); 
                                $(".form-group").prepend(openerp.qweb.render("fiscalYearAlert"));
                            }
                            else {
                                fy = fy[0];
                                $("input[name='date_to']").val(fy.date_stop);
                                $("input[name='date_from']").val(fy.date_start);
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
            dtTo = new Date(dtTo.substr(0, 4), dtTo.substr(5, 2) - 1, dtTo.substr(8, 2), 12, 0, 0, 0);
            if (!no_date_range) {
                var dtFrom = this.$("input[name='date_from']").val();
                dtFrom = new Date(dtFrom.substr(0, 4), dtFrom.substr(5, 2) - 1, dtFrom.substr(8, 2), 12, 0, 0, 0);
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
                this.$("input[name='date_from_cmp']").val(dtFrom.toISOString().substr(0, 10)); 
            }
            this.$("input[name='date_to_cmp']").val(dtTo.toISOString().substr(0, 10)); 

        }
    },
    footnoteFromDropdown: function(e) {
        e.stopPropagation();
        e.preventDefault();
        self = this;
        var report_name = $(e.target).parents("div.page").attr("class").split(/\s+/)[2];
        var context_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
        var model = new openerp.Model('account.report.context.common');
        model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            self.curFootNoteTarget = $(e.target).parents("div.dropdown").find("span.account_id");
            var contextModel = new openerp.Model(result);
            var type = $(e.target).parents('tr').attr("class").split(/\s+/)[0];
            var target_id = $(e.target).parents('tr').attr("class").split(/\s+/)[1];
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
        var par = $el.parents("div.summary")
        $el.parents("div.summary").html(openerp.qweb.render("editSummary", {summary: text}));
        par.find("textarea").height(height);
    },
    clickPencil: function(e) {
        e.stopPropagation();
        e.preventDefault();
        self = this;
        if ($(e.target).parent().is('.oe-account-next-action')) {
            self.setNextAction(e);
        }
        else if ($(e.target).parents("div.summary, p.footnote").length > 0) {
            var num = 0;
            if ($(e.target).parent().parent().is("p.footnote")) {
                var $el = $(e.target).parent().parent().find('span.text');
                var text = $el.html().replace(/\s+/g, ' ').replace(/\r?\n/g, '').replace(/<br>/g, '\n').replace(/(\n\s*)+$/g, '');
                text = text.split('.');
                var num = text[0];
                text = text[1];
                $el.html(openerp.qweb.render("editContent", {num: num, text: text}));
            }
            else {
                var $el = $(e.target).parents('div.savedSummary').children('span');
                var height = $el.height();
                var text = $el.html().replace(/\s+/g, ' ').replace(/\r?\n/g, '').replace(/<br>/g, '\n').replace(/(\n\s*)+$/g, '');
                var par = $el.parent()
                $el.replaceWith(openerp.qweb.render("editContent", {num: 0, text: text}));
                par.find("textarea").height(height);
            }
        }
        else if ($(e.target).parent().parent().find("sup").length == 0) {
            var report_name = $(e.target).parents("div.page").attr("class").split(/\s+/)[2];
            var context_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
            var model = new openerp.Model('account.report.context.common');
            model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                self.curFootNoteTarget = $(e.target).parent().parent();
                var contextModel = new openerp.Model(result);
                var type = $(e.target).parents('tr').attr("class").split(/\s+/)[0];
                var target_id = $(e.target).parents('tr').attr("class").split(/\s+/)[1];
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
        var report_name = $(e.target).parents("div.page").attr("class").split(/\s+/)[2];
        var context_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
        var text = $(e.target).siblings('textarea').val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        var footNoteSeqNum = $(e.target).parents('p.footnote').text().split('.')[0];
        if ($(e.target).parents("p.footnote").length > 0) {
            $(e.target).siblings('textarea').replaceWith(text);
            var model = new openerp.Model('account.report.context.common');
            model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                var contextModel = new openerp.Model(result);
                contextModel.call('edit_footnote', [[parseInt(context_id)], parseInt(footNoteSeqNum), text]);
            });
        }
        else {
            if (text != '')
                $(e.target).parents("div.summary").html(openerp.qweb.render("savedSummary", {summary : text}));
            else
                $(e.target).parents("div.summary").html(openerp.qweb.render("addSummary"));
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
        if ($(e.target).parents("div.summary").length > 0) {
            var report_name = $(e.target).parents("div.page").attr("class").split(/\s+/)[2];
            var context_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
            $(e.target).parent().parent().replaceWith(openerp.qweb.render("addSummary"));
            var model = new openerp.Model('account.report.context.common');
            model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                var contextModel = new openerp.Model(result);
                contextModel.call('edit_summary', [[parseInt(context_id)], '']);
            });
        }
        else {
            var num = $(e.target).parent().parent().text().split('.')[0];
            this.$("sup:contains('" + num + "')").remove();
            var report_name = $(e.target).parents("div.page").attr("class").split(/\s+/)[2];
            var context_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
            $(e.target).parent().parent().remove();
            var model = new openerp.Model('account.report.context.common');
            model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
                var contextModel = new openerp.Model(result);
                contextModel.call('remove_footnote', [[parseInt(context_id)], parseInt(num)]);
            });
        }
    },
    fold: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var report_name = $(e.target).parents("div.page").attr("class").split(/\s+/)[2];
        var context_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
        var el;
        var $el;
        var $nextEls = $(e.target).parents('tr').nextAll();
        for (el in $nextEls) {
            $el = $($nextEls[el]).find("td span[style='font-style: italic; margin-left: 70px']");
            if ($el.length == 0)
                break;
            else {
                $($el[0]).parents("tr").hide();
            }
        }
        var active_id = $(e.target).parents('tr').find('td.foldable').attr("class").split(/\s+/)[1];
        $(e.target).parents('tr').find('td.foldable').attr('class', 'unfoldable ' + active_id)
        $(e.target).parents('tr').find('span.foldable').replaceWith(openerp.qweb.render("unfoldable", {lineId: active_id}));
        var model = new openerp.Model('account.report.context.common');
        model.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            var contextModel = new openerp.Model(result);
            contextModel.call('remove_line', [[parseInt(context_id)], parseInt(active_id)]);
        });
    },
    unfold: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var report_name = $(e.target).parents("div.page").attr("class").split(/\s+/)[2];
        var context_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
        var active_id = $(e.target).parents('tr').find('td.unfoldable').attr("class").split(/\s+/)[1];
        var commonContext = new openerp.Model('account.report.context.common');
        commonContext.call('get_context_name_by_report_name', [report_name]).then(function (result) {
            var contextObj = new openerp.Model(result);
            contextObj.call('add_line', [[parseInt(context_id)], parseInt(active_id)]).then(function (result) {
                var el;
                var $el;
                var $nextEls = $(e.target).parents('tr').nextAll();
                var isLoaded = false;
                for (el in $nextEls) {
                    $el = $($nextEls[el]).find("td span[style='font-style: italic; margin-left: 100px']");
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
                $(e.target).parents('tr').find('td.unfoldable').attr('class', 'foldable ' + active_id)
                $(e.target).parents('tr').find('span.unfoldable').replaceWith(openerp.qweb.render("foldable", {lineId: active_id}));
            });
        });
    },
    displayMoveLinesByAccount: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).parents("div.dropdown").find("span.account_id").attr("class").split(/\s+/)[1];
        var model = new openerp.Model('ir.model.data');
        model.call('get_object_reference', ['account', 'action_move_line_select']).then(function (result) {
            window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
        });
    },
    displayMoveLinesByAccountGraph: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).parents("div.dropdown").find("span.account_id").attr("class").split(/\s+/)[1];
        var model = new openerp.Model('ir.model.data');
        model.call('get_object_reference', ['account', 'action_move_line_graph']).then(function (result) {
            window.open("/web?#view_type=graph&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
        });
    },
    displayMoveLinesByType: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).attr("class").split(/\s+/)[1];
        var model = new openerp.Model('ir.model.data');
        model.call('get_object_reference', ['account', 'action_move_line_select_by_type']).then(function (result) {
            window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
        });
    },
    displayFollowup: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).attr("class").split(/\s+/)[1];
        window.open("/account/followup_report/" + active_id);
    },
    displayNetTaxLines: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).parents("div.dropdown").find("span.tax_id").attr("class").split(/\s+/)[1];
        var model = new openerp.Model('ir.model.data');
        model.call('get_object_reference', ['account', 'act_account_tax_net']).then(function (result) {
            window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
        });
    },
    displayTaxLines: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).parents("div.dropdown").find("span.tax_id").attr("class").split(/\s+/)[1];
        var model = new openerp.Model('ir.model.data');
        model.call('get_object_reference', ['account', 'act_account_tax_tax']).then(function (result) {
            window.open("/web?#page=0&limit=80&view_type=list&model=account.move.line&action=" + result[1] + "&active_id=" + active_id, "_self");
        });
    },
    displayTax: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).attr("class").split(/\s+/)[1];
        window.open("/web?#id=" + active_id + "&view_type=form&model=account.tax", "_self");
    },
    displayMoveLine: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).attr("class").split(/\s+/)[1];
        window.open("/web?#id=" + active_id + "&view_type=form&model=account.move.line", "_self");
    },
    displayInvoice: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).parents("div.dropdown").find("span.unreconciled_aml").attr("class").split(/\s+/)[1];
        var model = new openerp.Model('account.move.line');
        model.query(['invoice'])
        .filter([['id', '=', active_id]]).first().then(function (result) {
            window.open("/web#id=" + result.invoice[0] + "&view_type=form&model=account.invoice", "_self");
        });
    },
    displayPayment: function(e) {
        e.stopPropagation();
        var active_id = $(e.target).parents("div.dropdown").find("span.unreconciled_aml").attr("class").split(/\s+/)[1];
        var model = new openerp.Model('account.move.line');
        model.query(['statement_id'])
        .filter([['id', '=', active_id]]).first().then(function (result) {
            window.open("/web#id=" + result.statement_id[0] + "&view_type=form&model=account.bank.statement", "_self");
        });
    },
});