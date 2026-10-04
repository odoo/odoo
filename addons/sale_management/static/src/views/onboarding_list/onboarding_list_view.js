import { patch } from '@web/core/utils/patch';
import { saleListView } from '@sale/views/sale_onboarding_list/sale_onboarding_list_view';

patch(saleListView, {
    buttonTemplate: 'sale_management.SaleManagementTemplateListView.Buttons',
});
