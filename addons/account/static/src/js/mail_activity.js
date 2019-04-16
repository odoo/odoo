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
        'click .see_all_activities': '_onOpenJournalSettings',
    },
    init: function () {
        this.MAX_ACTIVITY_DISPLAY = 5;
        this._super.apply(this, arguments);
    },
    //------------------------------------------------------------
    // Private
    //------------------------------------------------------------
    _render: function () {
        var self = this;
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

    _onOpenJournalSettings: function(e) {
        e.preventDefault();
        var self = this;
        self.do_action({
            target: 'current',
            res_id: self.res_id,
            type: 'ir.actions.act_window',
            res_model: 'account.journal',
            views: [[false, 'form']],
        });
    }
})

field_registry.add('kanban_vat_activity', VatActivity);

return VatActivity;
});
