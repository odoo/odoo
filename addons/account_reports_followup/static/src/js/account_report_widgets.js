odoo.define('account_followup.FollowupReportWidget', function (require) {
'use strict';

var core = require('web.core');
var FollowupWidget = require('account.FollowupReportWidget');
var Model = require('web.Model');

var QWeb = core.qweb;

var FollowupReportWidget = FollowupWidget.extend({
    events: _.defaults({
        'click .changeTrust': 'changeTrust',
        'click .followup-action': 'doManualAction',
    }, FollowupWidget.prototype.events),
    start: function() {
        QWeb.add_template("/account_reports_followup/static/src/xml/account_followup_report.xml");
        return this._super();
    },
    onKeyPress: function(e) {
        var report_name = $("div.page").data("report-name");
        if ((e.which === 13 || e.which === 10) && (e.ctrlKey || e.metaKey) && report_name == 'followup_report') {
            $("*[data-primary='1'].followup-email").trigger('click');
            var letter_context_list = [];
            $("*[data-primary='1'].followup-letter").each(function() {
                letter_context_list.push($(this).data('context'))
            });
            var action_context_list = [];
            $("*[data-primary='1'].followup-action").each(function() {
                action_context_list.push($(this).data('context'))
            });
            window.open('?pdf&letter_context_list=' + letter_context_list, '_blank');
            window.location.assign('?partner_done=all&action_context_list=' + action_context_list, '_self');
        }
    },
    changeTrust: function(e) {
        var partner_id = $(e.target).parents('span.dropdown').data("partner");
        var newTrust = $(e.target).data("new-trust");
        var color = 'grey';
        switch(newTrust) {
            case 'good':
                color = 'green';
                break;
            case 'bad':
                color = 'red'
                break;
        }
        return new Model('res.partner').call('write', [[parseInt(partner_id)], {'trust': newTrust}]).then(function (result) {
            $(e.target).parents('span.dropdown').find('i.oe-account_followup-trust').attr('style', 'color: ' + color + '; font-size: 0.8em;')
        });
    },
    doManualAction: function(e) {
        e.stopPropagation();
        e.preventDefault();
        var context_id = $(e.target).parents("div.page").data("context");
        return new Model('account.report.context.followup').call('do_manual_action', [[parseInt(context_id)]]).then (function (result) {
            if ($(e.target).data('primary') == '1') {
                $(e.target).parents('#action-buttons').addClass('oe-account-followup-clicked');
                $(e.target).toggleClass('btn-primary btn-default');
                $(e.target).data('primary', '0');
            }
        });
    },

});

return FollowupReportWidget;

});