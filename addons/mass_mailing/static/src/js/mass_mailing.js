odoo.define('mass_mailing.mass_mailing', function (require) {

var core = require('web.core');
var KanbanRecord = require('web_kanban.Record');
var KanbanView = require('web_kanban.KanbanView');

var _t = core._t;

KanbanRecord.include({
    on_card_clicked: function (event) {
        if (this.model === 'mail.mass_mailing.campaign') {
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
