odoo.define('utm.CampaignKanbanView', function (require) {
"use strict";

var UtmCampaignKanbanRenderer = require('utm.CampaignKanbanRenderer');

var KanbanView = require('web.KanbanView');
var view_registry = require('web.view_registry');

var UtmCampaignKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Renderer: UtmCampaignKanbanRenderer,
    }),
});

view_registry.add('utm_campaign_kanban', UtmCampaignKanbanView);

return UtmCampaignKanbanView;

});
