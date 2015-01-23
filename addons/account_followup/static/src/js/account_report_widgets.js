openerp.account_followup = openerp.account_followup || {}

openerp.account_followup.FollowupReportWidgets = openerp.account.FollowupReportWidgets.extend({
    events: _.defaults({
        'click .changeTrust': 'changeTrust',
        'click .followup-action': 'doManualAction',
    }, openerp.account.FollowupReportWidgets.prototype.events),
    start: function() {
        openerp.qweb.add_template("/account_followup/static/src/xml/account_followup_report.xml");
        return this._super();
    },
    onKeyPress: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var report_name = $("div.page").attr("class").split(/\s+/)[2];
        if ((e.which === 13 || e.which === 10) && (e.ctrlKey || e.metaKey) && report_name == 'followup_report') {
            $('a.btn-primary.followup-email').trigger('click');
            $('a.btn-primary.followup-letter').trigger('click');
            var action_context_list = [];
            $('a.btn-primary.followup-action').each(function() {
                action_context_list.push($(this).attr('context'))
            });
            window.open('?partner_done=all&action_context_list=' + action_context_list, '_self');
        }
    },
    changeTrust: function(e) {
        var partner_id = $(e.target).parents('span.dropdown').attr("partner");
        var newTrust = $(e.target).attr("new-trust");
        var color = 'grey';
        switch(newTrust) {
            case 'good':
                color = 'green';
                break;
            case 'bad':
                color = 'red'
                break;
        }
        var model = new openerp.Model('res.partner');
        model.call('write', [[parseInt(partner_id)], {'trust': newTrust}]).then(function (result) {
            $(e.target).parents('span.dropdown').find('i.oe-account_followup-trust').attr('style', 'color: ' + color + '; font-size: 0.8em;')
        });
    },
    doManualAction: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var context_id = $(e.target).parents("div.page").attr("class").split(/\s+/)[3];
        var contextModel = new openerp.Model('account.report.context.followup');
        contextModel.call('do_manual_action', [[parseInt(context_id)]]).then (function (result) {
            var $skipButton = $(e.target).siblings('a.followup-skip');
            $skipButton.attr('class', 'btn btn-primary followup-skip');
            $skipButton.text('Done');
            $(e.target).attr('class', 'btn btn-default followup-letter');
        });
    }
});
