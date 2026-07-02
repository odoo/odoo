import { registry } from '@web/core/registry';
import { SaleListRenderer } from '../sale_onboarding_list/sale_onboarding_list_renderer';
import { saleFileUploadListView } from '../sale_file_upload_list/sale_file_upload_list_view';
import { Dashboard } from '../../js/dashboard/dashboard';

export class DashboardListRenderer extends SaleListRenderer {
    static template = 'sale.ListRenderer';
    static components = {
        ...SaleListRenderer.components,
        Dashboard,
    };
}

export const dashboardListView = Object.assign(Object.create(saleFileUploadListView), {
    Renderer: DashboardListRenderer,
});

registry.category('views').add('sale_dashboard_list', dashboardListView);
