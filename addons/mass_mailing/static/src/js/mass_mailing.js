odoo.define('mass_mailing.mass_mailing', function (require) {

var FieldTextHtml = require('web_editor.backend').FieldTextHtml;
var KanbanRecord = require('web.KanbanRecord');
var KanbanColumn = require('web.KanbanColumn');

KanbanRecord.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _openRecord: function () {
        if (this.modelName === 'mail.mass_mailing.campaign') {
            this.$('.oe_mailings').click();
        } else {
            this._super.apply(this, arguments);
        }
    },
});

KanbanColumn.include({
    init: function () {
        this._super.apply(this, arguments);
        if (this.modelName === 'mail.mass_mailing') {
            this.draggable = false;
        }
    },
});

FieldTextHtml.include({
    getDatarecord: function () {
        /* Avoid extremely long URIs by whitelisting fields in the datarecord
        that get set as a get parameter */
        var datarecord = this._super();
        if (this.model === 'mail.mass_mailing') {
            // these fields can potentially get very long, let's remove them
            datarecord = _.omit(datarecord, ['mailing_domain', 'contact_list_ids', 'body_html']);
        }
        return datarecord;
    },
});

});
