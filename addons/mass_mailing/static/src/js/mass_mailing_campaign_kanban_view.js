odoo.define('mass_mailing.CampaignKanbanView', function (require) {
"use strict";

var MassMailingCampaignKanbanRenderer = require('mass_mailing.CampaignKanbanRenderer');

var KanbanView = require('web.KanbanView');
var view_registry = require('web.view_registry');

var MassMailingCampaignKanbanView = KanbanView.extend({
    config: _.extend({}, KanbanView.prototype.config, {
        Renderer: MassMailingCampaignKanbanRenderer,
    }),
});

view_registry.add('mass_mailing_campaign_kanban', MassMailingCampaignKanbanView);

return MassMailingCampaignKanbanView;

});
