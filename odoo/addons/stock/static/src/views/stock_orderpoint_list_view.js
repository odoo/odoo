/** @odoo-module */

import { listView } from '@web/views/list/list_view';
import { registry } from "@web/core/registry";
import { StockOrderpointListController as Controller } from './stock_orderpoint_list_controller';

export const StockOrderpointListView = {
    ...listView,
    Controller,
    buttonTemplate: 'stock.StockOrderpoint.Buttons',
};

registry.category("views").add("stock_orderpoint_list", StockOrderpointListView);
