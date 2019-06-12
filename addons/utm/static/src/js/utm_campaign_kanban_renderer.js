odoo.define('utm.CampaignKanbanRenderer', function (require) {
"use strict";

var UtmCampaignKanbanRecord = require('utm.CampaignKanbanRecord');

var KanbanRenderer = require('web.KanbanRenderer');

var UtmCampaignKanbanRenderer = KanbanRenderer.extend({
    config: _.extend({}, KanbanRenderer.prototype.config, {
        KanbanRecord: UtmCampaignKanbanRecord,
    }),
});

return UtmCampaignKanbanRenderer;

});
