/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { formatFloatTime, formatFloat } from "@web/views/fields/formatters";
import { ProjectRightSidePanel } from '@project/components/project_right_side_panel/project_right_side_panel';

patch(ProjectRightSidePanel.prototype, '@sale_project/components/project_right_side_panel/project_right_side_panel', {
    async _loadAdditionalSalesOrderItems() {
        const offset = this.state.data.sale_items.data.length;
        const totalRecords = this.state.data.sale_items.total;
        const limit = totalRecords - offset <= 5 ? totalRecords - offset : 5;
        const saleOrderItems = await this.orm.call(
            'project.project',
            'get_sale_items_data',
            [this.projectId, undefined, offset, limit],
            {
                context: this.context,
            },
        );
        this.state.data.sale_items.data = [...this.state.data.sale_items.data, ...saleOrderItems];
    },

    async onLoadSalesOrderLinesClick() {
        const saleItems = this.state.data.sale_items;
        if (saleItems && saleItems.total > saleItems.data.length) {
            await this._loadAdditionalSalesOrderItems();
        }
    },

    formatValue(value, unit) {
        return unit === 'Hours' ? formatFloatTime(value) : formatFloat(value);
    },

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    /**
     * @private
     * @param {Object} params
     */
    async onSaleItemActionClick(params) {
        if (params.resId && params.type !== 'object') {
            const action = await this.actionService.loadAction(params.name, this.context);
            this.actionService.doAction({
                ...action,
                res_id: params.resId,
                views: [[false, 'form']]
            });
        } else {
            this.onProjectActionClick(params);
        }
    },

});
