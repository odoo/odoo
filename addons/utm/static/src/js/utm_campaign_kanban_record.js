odoo.define('utm.CampaignKanbanRecord', function (require) {
"use strict";

var KanbanRecord = require('web.KanbanRecord');

var UtmCampaignKanbanRecord = KanbanRecord.extend({
    /**
     * @override
     * @private
     */
    _openRecord: function () {
        this.$('.oe_mailings').click();
    }
});

return UtmCampaignKanbanRecord;

});
