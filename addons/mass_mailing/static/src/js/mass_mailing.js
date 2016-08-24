odoo.define('mass_mailing.mass_mailing', function (require) {

var core = require('web.core');
var FieldTextHtml = require('web_editor.backend').FieldTextHtml;
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

FieldTextHtml.include({
    get_datarecord: function() {
        /* Avoid extremely long URIs by whitelisting fields in the datarecord
        that get set as a get parameter */
        var datarecord = this._super();
        if (this.view.model === 'mail.mass_mailing') {
            // these fields can potentially get very long, let's remove them
            var blacklist = ['mailing_domain', 'contact_list_ids'];
            for (var k in blacklist) {
                delete datarecord[blacklist[k]];
            }
            delete datarecord[this.name];
        }
        return datarecord;
    },
});

});
