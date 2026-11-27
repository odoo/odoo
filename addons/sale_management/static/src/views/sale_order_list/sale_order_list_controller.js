import { SaleOrderListController } from '@sale/views/sale_order_list/sale_order_list_controller';
import { SaleTemplateDropdown } from '@sale_management/views/components/template_dropdown';
import { patch } from '@web/core/utils/patch';

patch(SaleOrderListController, {
    components: {
        ...SaleOrderListController.components,
        SaleTemplateDropdown,
    },
});
