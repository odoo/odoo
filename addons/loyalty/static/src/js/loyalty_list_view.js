/** @odoo-module **/

import { LoyaltyModelMixin, LoyaltyRendererMixin } from "@loyalty/js/loyalty_views";
import ListModel from 'web.ListModel';
import ListRenderer from 'web.ListRenderer';
import ListView from 'web.ListView';
import viewRegistry from 'web.view_registry';

export const LoyaltyListModel = ListModel.extend(LoyaltyModelMixin);
export const LoyaltyListRenderer = ListRenderer.extend(LoyaltyRendererMixin, {
    events: _.extend({}, ListRenderer.prototype.events, {
        'click .loyalty-template': '_onTemplateClick',
    }),
});

export const LoyaltyListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Model: LoyaltyListModel,
        Renderer: LoyaltyListRenderer,
    })
});

viewRegistry.add('loyalty_program_list_view', LoyaltyListView);
