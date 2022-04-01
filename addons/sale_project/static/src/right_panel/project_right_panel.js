/** @odoo-module  */

import { patch } from 'web.utils';
import ProjectRightPanel from '@project/js/right_panel/project_right_panel';

patch(ProjectRightPanel.prototype, '@sale_project/right_panel/project_right_panel', {
    async _loadAdditionalSalesOrderItems() {
        const offset = this.state.data.sale_items.data.length;
        const totalRecords = this.state.data.sale_items.total;
        const limit = totalRecords - offset <= 10 ? totalRecords - offset : 10;
        const saleOrderItems = await this.rpc({
            model: 'project.project',
            method: 'get_sale_items_data',
            args: [this.project_id, undefined, offset, limit],
            kwargs: {
                context: this.context,
            }
        });
        this.state.data.sale_items.data = [...this.state.data.sale_items.data, ...saleOrderItems];
    },

    async onLoadSalesOrderLinesClick() {
        const saleItems = this.state.data.sale_items;
        if (saleItems && saleItems.total > saleItems.data.length) {
            await this._loadAdditionalSalesOrderItems();
        }
    }
});
