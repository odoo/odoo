odoo.define('mass_mailing.CampaignKanbanRenderer', function (require) {
"use strict";

var MassMailingCampaignKanbanRecord = require('mass_mailing.CampaignKanbanRecord');

var KanbanRenderer = require('web.KanbanRenderer');

var MassMailingCampaignKanbanRenderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord: MassMailingCampaignKanbanRecord,
    }),
});

return MassMailingCampaignKanbanRenderer;

});
