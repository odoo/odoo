/** @odoo-module **/

import ListView from 'web.ListView';
import PurchaseOrderLineCompareListController from '@purchase_requisition/js/purchase_order_line_compare_list_controller';
import PurchaseOrderLineCompareListRenderer from '@purchase_requisition/js/purchase_order_line_compare_list_renderer';
import viewRegistry from 'web.view_registry';

const PurchaseOrderLineCompareListView = ListView.extend({
    config: Object.assign({}, ListView.prototype.config, {
        Controller: PurchaseOrderLineCompareListController,
        Renderer: PurchaseOrderLineCompareListRenderer,
    }),
});

viewRegistry.add('purchase_order_line_compare', PurchaseOrderLineCompareListView);

export default PurchaseOrderLineCompareListView;
