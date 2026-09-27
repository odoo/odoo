import { patch } from '@web/core/utils/patch';
import { SaleListView } from '@sale/views/sale_onboarding_list/sale_onboarding_list_view';

patch(SaleListView, {
    buttonTemplate: 'sale_management.SaleManagementTemplateListView.Buttons',
});
