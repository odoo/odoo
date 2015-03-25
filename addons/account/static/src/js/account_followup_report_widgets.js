openerp.account.FollowupReportWidgets = openerp.account.ReportWidgets.extend({
    events: _.defaults({
        'click .change_exp_date': 'displayExpNoteModal',
        'click #savePaymentDate': 'changeExpDate',
        'click .followup-email': 'sendFollowupEmail',
        'click .followup-letter': 'printFollowupLetter',
        'click .followup-skip': 'skipPartner',
        'click .followup-done': 'donePartner',
        "change *[name='blocked']": 'onChangeBlocked',
        'click .oe-account-set-next-action': 'setNextAction',
        'click #saveNextAction': 'saveNextAction',
        'click .oe-account-followup-set-next-action': 'setNextAction',
    }, openerp.account.ReportWidgets.prototype.events),
    saveNextAction: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var note = $("#nextActionNote").val().replace(/\r?\n/g, '<br />').replace(/\s+/g, ' ');
        var target_id = $("#nextActionModal #target_id").val();
        var date = $("#nextActionDate").val();
        date = openerp.web.parse_value(date, {type:'date'})
        var contextModel = new openerp.Model('account.report.context.followup');
        return contextModel.call('change_next_action', [[parseInt(target_id)], date, note]).then(function (result) {
            $('#nextActionModal').modal('hide');
            $('div.page.' + target_id).find('.oe-account-next-action').html(openerp.qweb.render("nextActionDate", {'note': note, 'date': date}));
        });
    },
    setNextAction: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var target_id = $(e.target).parents("div.page").data('context');
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
        var target_id = $(e.target).parents('tr').data('id');
        var model = new openerp.Model('account.move.line');
        model.call('write', [[parseInt(target_id)], {'blocked': checkbox}])
    },
    onKeyPress: function(e) {
        var report_name = $("div.page").data("report-name");
        if ((e.which === 13 || e.which === 10) && (e.ctrlKey || e.metaKey) && report_name == 'followup_report') {
            $("*[data-primary='1'].followup-email").trigger('click');
            var letter_context_list = [];
            $("*[data-primary='1'].followup-letter").each(function() {
                letter_context_list.push($(this).data('context'))
            });
            window.open('?pdf&letter_context_list=' + letter_context_list, '_blank');
            window.open('?partner_done=all', '_self');
        }
    },
    donePartner: function(e) {
        var partner_id = $(e.target).data("partner");
        var model = new openerp.Model('res.partner');
        return model.call('update_next_action', [[parseInt(partner_id)]]).then(function (result) {
            window.open('?partner_done=' + partner_id, '_self');
        });
    },
    skipPartner: function(e) {
        var partner_id = $(e.target).data("partner");
        var model = new openerp.Model('res.partner');
        window.open('?partner_skipped=' + partner_id, '_self');
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
        var contextModel = new openerp.Model('account.report.context.followup');
        return contextModel.call('send_email', [[parseInt(context_id)]]).then (function (result) {
            if (result == true) {
                window.$("div.page:first").prepend(openerp.qweb.render("emailSent"));
                if ($(e.target).data('primary') == '1') {
                    $(e.target).parents('#action-buttons').addClass('oe-account-followup-clicked');
                    $(e.target).toggleClass('btn-primary btn-default');
                    $(e.target).data('primary', '0');
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
        var amlModel = new openerp.Model('account.move.line');
        return amlModel.call('write', [[parseInt($("#paymentDateModal #target_id").val())], {expected_pay_date: openerp.web.parse_value($("#expectedDate").val(), {type:'date'}), internal_note: note}]).then(function (result) {
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
        ZeroClipboard.config({swfPath: location.origin + "/web/static/lib/zeroclipboard/ZeroClipboard.swf" });
        var zc = new ZeroClipboard($(".btn_share_url"));
        zc.on('ready', function(e) {
            zc.on('aftercopy', function(e) {
                $(e.target).text('Copied !');
            });
        });
        $(document).on("keypress", this, this.onKeyPress);
        return this._super();
    },
})