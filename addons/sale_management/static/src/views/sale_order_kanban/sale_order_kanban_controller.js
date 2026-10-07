import { SaleOrderKanbanController } from '@sale/views/sale_order_kanban/sale_order_kanban_controller';
import { SaleTemplateDropdown } from '@sale_management/views/components/template_dropdown';
import { patch } from '@web/core/utils/patch';

patch(SaleOrderKanbanController, {
    components: {
        ...SaleOrderKanbanController.components,
        SaleTemplateDropdown,
    },
});
