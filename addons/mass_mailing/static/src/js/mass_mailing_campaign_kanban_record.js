odoo.define('mass_mailing.CampaignKanbanRecord', function (require) {
"use strict";

var KanbanRecord = require('web.KanbanRecord');

var MassMailingCampaignKanbanRecord = KanbanRecord.extend({
    /**
     * @override
     * @private
     */
    _openRecord: function () {
        this.$('.oe_mailings').click();
    }
});

return MassMailingCampaignKanbanRecord;

});
