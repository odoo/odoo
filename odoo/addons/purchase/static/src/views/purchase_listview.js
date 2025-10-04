/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { PurchaseDashBoard } from '@purchase/views/purchase_dashboard';

export class PurchaseDashBoardRenderer extends ListRenderer {};

PurchaseDashBoardRenderer.template = 'purchase.PurchaseListView';
PurchaseDashBoardRenderer.components= Object.assign({}, ListRenderer.components, {PurchaseDashBoard})

export const PurchaseDashBoardListView = {
    ...listView,
    Renderer: PurchaseDashBoardRenderer,
};

registry.category("views").add("purchase_dashboard_list", PurchaseDashBoardListView);
