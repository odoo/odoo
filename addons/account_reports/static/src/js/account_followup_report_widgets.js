odoo.define('account.FollowupReportWidget', function (require) {
'use strict';

var core = require('web.core');
var Model = require('web.Model');
var formats = require('web.formats');
var ReportWidget = require('account.ReportWidget');
var time = require('web.time');

var QWeb = core.qweb;

var FollowupReportWidget = ReportWidget.extend({
    events: _.defaults({
        'click .change_exp_date': 'displayExpNoteModal',
        'click #savePaymentDate': 'changeExpDate',
        'click .followup-email': 'sendFollowupEmail',
        'click .followup-letter': 'printFollowupLetter',
        'click .followup-skip': 'skipPartner',
        'click .followup-done': 'donePartner',
        'click .oe-account-followup-auto': 'enableAuto',
        "change *[name='blocked']": 'onChangeBlocked',
        'click .oe-account-set-next-action': 'setNextAction',
        'click #saveNextAction': 'saveNextAction',
        'click .oe-account-followup-set-next-action': 'setNextAction',
    }, ReportWidget.prototype.events),
    saveNextAction: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var note = $("#nextActionNote").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        var target_id = $("#nextActionModal #target_id").val();
        var date = $("#nextActionDate").val();
        date = formats.parse_value(date, {type:'date'})
        return new Model('account.report.context.followup').call('change_next_action', [[parseInt(target_id)], date, note]).then(function (result) {
            $('#nextActionModal').modal('hide');
            $('div.page.' + target_id).find('.oe-account-next-action').html(QWeb.render("nextActionDate", {'note': note, 'date': date}));
        });
    },
    enableAuto: function(e) {
        var target_id;
        if ($(e.target).is('.btn-default')) { // change which button is highlighted
            target_id = $(e.target).parents("div.page").data('context');
            $(e.target).toggleClass('btn-default btn-info');
            $(e.target).siblings().toggleClass('btn-default btn-info');
            $(e.target).parents("div.page").find('.oe-account-followup-no-action').remove();
        }
        else if ($(e.target).is('div.alert a')) {
            target_id = $("div.page").data('context');
            $("div.page").find('div#followup-mode .oe-account-followup-auto').addClass('btn-info');
            $("div.page").find('div#followup-mode .oe-account-followup-auto').removeClass('btn-default');
            $("div.page").find('div#followup-mode .oe-account-followup-manual').addClass('btn-default');
            $("div.page").find('div#followup-mode .oe-account-followup-manual').removeClass('btn-info');
            $('.oe-account-followup-no-action').remove();
        }
        return new Model('account.report.context.followup').call('to_auto', [[parseInt(target_id)]])
    },
    setNextAction: function(e) {
        e.stopPropagation();
        e.preventDefault();
        if ($(e.target).is('.oe-account-followup-manual.btn-default')){
            $(e.target).toggleClass('btn-default btn-info');
            $(e.target).siblings().toggleClass('btn-default btn-info');
        }
        if ($(e.target).parents("div.page").length > 0){
            var target_id = $(e.target).parents("div.page").data('context');
            $("#nextActionModal #target_id").val(target_id);
        }
        var dt = new Date();
        switch($(e.target).data('time')) {
            case 'one-week':
                dt.setDate(dt.getDate() + 7);
                break;
            case 'two-weeks':
                dt.setDate(dt.getDate() + 14);
                break;
            case 'one-month':
                dt.setMonth(dt.getMonth() + 1);
                break;
            case 'two-months':
                dt.setMonth(dt.getMonth() + 2);
                break;
        }
        $('.oe-account-picker-next-action-date').data("DateTimePicker").setValue(moment(dt));
        $('#nextActionModal').on('hidden.bs.modal', function (e) {
            $(this).find('form')[0].reset();
        });
        $('#nextActionModal').modal('show');
    },
    onChangeBlocked: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var checkbox = $(e.target).is(":checked")
        var target_id = $(e.target).parents('tr').data('id');
        if (checkbox) {
            $(e.target).parents('tr').attr('bgcolor', 'LightGray');
        }
        else {
            $(e.target).parents('tr').attr('bgcolor', 'white');
        }
        return new Model('account.move.line').call('write', [[parseInt(target_id)], {'blocked': checkbox}])
    },
    onKeyPress: function(e) {
        var report_name = $("div.page").data("report-name");
        if ((e.which === 13 || e.which === 10) && (e.ctrlKey || e.metaKey) && report_name == 'followup_report') {
            var letter_context_list = [];
            var email_context_list = [];
            $("*[data-primary='1'].followup-email").each(function() {
                email_context_list.push($(this).data('context'))
            });
            $("*[data-primary='1'].followup-letter").each(function() {
                letter_context_list.push($(this).data('context'))
            });
            window.open('?pdf&letter_context_list=' + letter_context_list, '_blank');
            window.location.assign('?partner_done=all&email_context_list=' + email_context_list, '_self');
        }
    },
    donePartner: function(e) {
        var partner_id = $(e.target).data("partner");
        return new Model('res.partner').call('update_next_action', [[parseInt(partner_id)]]).then(function (result) {
            window.location.assign('?partner_done=' + partner_id, '_self');
        });
    },
    skipPartner: function(e) {
        var partner_id = $(e.target).data("partner");
        window.location.assign('?partner_skipped=' + partner_id, '_self');
    },
    printFollowupLetter: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var url = $(e.target).data("target");
        window.open(url, '_blank');
        if ($(e.target).data('primary') == '1') {
            $(e.target).parents('#action-buttons').addClass('oe-account-followup-clicked');
            $(e.target).toggleClass('btn-primary btn-default');
            $(e.target).data('primary', '0');
        }
    },
    sendFollowupEmail: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var context_id = $(e.target).parents("div.page").attr("data-context");
        return new Model('account.report.context.followup').call('send_email', [[parseInt(context_id)]]).then (function (result) {
            if (result == true) {
                window.$("div.page:first").prepend(QWeb.render("emailSent"));
                if ($(e.target).data('primary') == '1') {
                    $(e.target).parents('#action-buttons').addClass('oe-account-followup-clicked');
                    $(e.target).toggleClass('btn-primary btn-default');
                    $(e.target).data('primary', '0');
                }
            }
            else {
                window.$("div.page:first").prepend(QWeb.render("emailNotSent"));
            }
        });
    },
    displayExpNoteModal: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var target_id = $(e.target).parents('tr').data('id');
        $("#paymentDateLabel").text($(e.target).parents("div.dropdown").find("span.invoice_id").text());
        $("#paymentDateModal #target_id").val(target_id);
        $('#paymentDateModal').on('hidden.bs.modal', function (e) {
            $(this).find('form')[0].reset();
        });
        $('#paymentDateModal').modal('show');
    },
    changeExpDate: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var note = $("#internalNote").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        return new Model('account.move.line').call('write', [[parseInt($("#paymentDateModal #target_id").val())], {expected_pay_date: formats.parse_value($("#expectedDate").val(), {type:'date'}), internal_note: note}]).then(function (result) {
            $('#paymentDateModal').modal('hide');
            location.reload(true);
        });
    },
    clickPencil: function(e) {
        e.stopPropagation();
        e.preventDefault();
        self = this;
        if ($(e.target).parent().hasClass('oe-account-next-action')) {
            self.setNextAction(e);
        }
        return this._super()
    },
    start: function() {
        $(document).on("keypress", this, this.onKeyPress);
        var l10n = core._t.database.parameters;
        var $datetimepickers = $('.oe-account-datetimepicker');
        var options = {
            language : moment.locale(),
            format : time.strftime_to_moment_format(l10n.date_format),
            icons: {
                date: "fa fa-calendar",
            },
            pickTime: false,
        }
        $datetimepickers.each(function () {
            $(this).datetimepicker(options);
        })
        return this._super();
    },

});

return FollowupReportWidget;
});