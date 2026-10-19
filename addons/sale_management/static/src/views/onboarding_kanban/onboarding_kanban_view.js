import { patch } from '@web/core/utils/patch';
import { saleKanbanView } from '@sale/views/sale_onboarding_kanban/sale_onboarding_kanban_view';

patch(saleKanbanView, {
    buttonTemplate: 'sale_management.SaleManagementTemplateKanbanView.Buttons',
});
