openerp.account.FollowupReportWidgets = openerp.account.ReportWidgets.extend({
    events: _.defaults({
        'click .change_exp_date': 'displayExpNoteModal',
        'click #savePaymentDate': 'changeExpDate',
        'click .followup-email': 'sendFollowupEmail',
        'click .followup-letter': 'printFollowupLetter',
        'click .followup-skip': 'skipPartner',
        "change *[name='blocked']": 'onChangeBlocked',
        'click .oe-account-set-next-action': 'setNextAction',
        'click #saveNextAction': 'saveNextAction',
        'click .oe-account-followup-one-week': 'setNextAction',
        'click .oe-account-followup-two-weeks': 'setNextAction',
        'click .oe-account-followup-one-month': 'setNextAction',
        'click .oe-account-followup-two-months': 'setNextAction',
    }, openerp.account.ReportWidgets.prototype.events),
    saveNextAction: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var note = $("#nextActionNote").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        var target_id = $("#nextActionModal #target_id").val();
        var date = $("#nextActionDate").val();
        var contextModel = new openerp.Model('account.report.context.followup');
        contextModel.call('change_next_action', [[parseInt(target_id)], date, note]).then(function (result) {
            $('#nextActionModal').modal('hide');
            date = new Date(date.substr(0, 4), date.substr(5, 2), date.substr(8, 2), 12, 0, 0, 0).toLocaleDateString();
            $('div.page.' + target_id).find('.oe-account-next-action').html(openerp.qweb.render("nextActionDate", {'note': note, 'date': date}));
        });
    },
    setNextAction: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var target_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
        var dt = new Date();
        switch($(e.target).attr("class").split(/\s+/)[2]) {
            case 'oe-account-followup-one-week':
                dt.setDate(dt.getDate() + 7);
                break;
            case 'oe-account-followup-two-weeks':
                dt.setDate(dt.getDate() + 14);
                break;
            case 'oe-account-followup-one-month':
                dt.setMonth(dt.getMonth() + 1);
                break;
            case 'oe-account-followup-two-months':
                dt.setMonth(dt.getMonth() + 2);
                break;
        }
        $("#nextActionModal #nextActionDate").val(dt.toISOString().substr(0, 10));
        $("#nextActionModal #target_id").val(target_id);
        $('#nextActionModal').on('hidden.bs.modal', function (e) {
            $(this).find('form')[0].reset();
        });
        $('#nextActionModal').modal('show');
    },
    onChangeBlocked: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var checkbox = $(e.target).is(":checked")
        var target_id = $(e.target).parents('tr').attr("class").split(/\s+/)[1];
        var model = new openerp.Model('account.move.line');
        model.call('write', [[parseInt(target_id)], {'blocked': checkbox}])
    },
    onKeyPress: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var report_name = $("div.page").attr("class").split(/\s+/)[2];
        if ((e.which === 13 || e.which === 10) && (e.ctrlKey || e.metaKey) && report_name == 'followup_report') {
            $('a.btn-primary.followup-email').trigger('click');
            var letter_context_list = [];
            $('a.btn-primary.followup-letter').each(function() {
                letter_context_list.push($(this).attr('context'))
            });
            window.open('?pdf&letter_context_list=' + letter_context_list, '_blank');
            window.open('?partner_done=all', '_self');
        }
    },
    skipPartner: function(e) {
        var partner_id = $(e.target).attr("partner");
        var model = new openerp.Model('res.partner');
        if ($(e.target).attr('class') == 'btn btn-primary followup-skip') {
            model.call('update_next_action', [[parseInt(partner_id)]]).then(function (result) {
                window.open('?partner_done=' + partner_id, '_self');
            });
        }
        else {
            window.open('?partner_skipped=' + partner_id, '_self');
        }
    },
    printFollowupLetter: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var url = $(e.target).attr("target");
        window.open(url, '_blank');
        if ($(e.target).attr("class").split(/\s+/)[1] == 'btn-primary') {
            var $skipButton = $(e.target).siblings('a.followup-skip');
            $skipButton.attr('class', 'btn btn-primary followup-skip');
            $skipButton.text('Done');
            $(e.target).attr('class', 'btn btn-default followup-letter');
        }
    },
    sendFollowupEmail: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var context_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
        var contextModel = new openerp.Model('account.report.context.followup');
        contextModel.call('send_email', [[parseInt(context_id)]]).then (function (result) {
            if (result == true) {
                window.$("div.page:first").prepend(openerp.qweb.render("emailSent"));
                if ($(e.target).attr("class").split(/\s+/)[1] == 'btn-primary') {
                    var $skipButton = $(e.target).siblings('a.followup-skip');
                    $skipButton.attr('class', 'btn btn-primary followup-skip');
                    $skipButton.text('Done');
                    $(e.target).attr('class', 'btn btn-default followup-email')
                }
            }
            else {
                window.$("div.page:first").prepend(openerp.qweb.render("emailNotSent"));
            }
        });
    },
    displayExpNoteModal: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var target_id = $(e.target).parents('tr').attr("class").split(/\s+/)[1];
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
        var invoiceModel = new openerp.Model('account.move.line');
        invoiceModel.call('write', [[parseInt($("#paymentDateModal #target_id").val())], {expected_pay_date: $("#expectedDate").val(), internal_note: note}]).then(function (result) {
            $('#paymentDateModal').modal('hide');
            location.reload(true);
        });
    },
    clickPencil: function(e) {
        e.stopPropagation();
        e.preventDefault();
        self = this;
        if ($(e.target).parent().is('.oe-account-next-action')) {
            self.setNextAction(e);
        }
        return this._super()
    },
    start: function() {
        ZeroClipboard.config({swfPath: location.origin + "/account/static/lib/zeroclipboard/ZeroClipboard.swf" });
        new ZeroClipboard($(".btn_share_url"));
        $(document).on("keypress", this, this.onKeyPress);
        return this._super();
    },
})