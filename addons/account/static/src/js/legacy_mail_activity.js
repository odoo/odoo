odoo.define('account.activity', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');

var QWeb = core.qweb;
var _t = core._t;

var VatActivity = AbstractField.extend({
    className: 'o_journal_activity_kanban',
    events: {
        'click .see_all_activities': '_onOpenAll',
        'click .see_activity': '_onOpenActivity',
    },
    init: function () {
        this.MAX_ACTIVITY_DISPLAY = 5;
        this._super.apply(this, arguments);
    },
    //------------------------------------------------------------
    // Private
    //------------------------------------------------------------
    _render: function () {
        var info = JSON.parse(this.value);
        if (!info) {
            this.$el.html('');
            return;
        }
        info.more_activities = false;
        if (info.activities.length > this.MAX_ACTIVITY_DISPLAY) {
            info.more_activities = true;
            info.activities = info.activities.slice(0, this.MAX_ACTIVITY_DISPLAY);
        }
        this.$el.html(QWeb.render('accountJournalDashboardActivity', info));
    },

    _onOpenActivity: function(e) {
        e.preventDefault();
        var self = this;
        self.do_action({
            type: 'ir.actions.act_window',
            name: _t('Journal Entry'),
            target: 'current',
            res_id: $(e.target).data('resId'),
            res_model:  'account.move',
            views: [[false, 'form']],
        });
    },

    _onOpenAll: function(e) {
        e.preventDefault();
        var self = this;
        self.do_action({
            type: 'ir.actions.act_window',
            name: _t('Journal Entries'),
            res_model:  'account.move',
            views: [[false, 'kanban'], [false, 'form']],
            search_view_id: [false],
            domain: [['journal_id', '=', self.res_id], ['activity_ids', '!=', false]],
        });
    }
})

field_registry.add('kanban_vat_activity', VatActivity);

return VatActivity;
});
