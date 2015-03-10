odoo.define('mass_mailing.mass_mailing', ['web.core', 'web_kanban.common', 'web_kanban.KanbanView'], function (require) {

var core = require('web.core');
var common = require('web_kanban.common');
var KanbanView = require('web_kanban.KanbanView');

var _t = core._t;

common.KanbanRecord.include({
    on_card_clicked: function (event) {
        if (this.view.dataset.model === 'mail.mass_mailing.campaign') {
            this.$('.oe_mailings').click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});

KanbanView.include({
    on_groups_started: function() {
        this._super.apply(this, arguments);
        if (this.dataset.model === 'mail.mass_mailing') {  
            this.$el.find('.oe_kanban_draghandle').removeClass('oe_kanban_draghandle');
        }
    },
});

});
