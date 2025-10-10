import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';
import { ListRenderer } from '@web/views/list/list_renderer';
import { WebsiteSaleDashboard } from '../js/website_sale_dashboard/website_sale_dashboard';

export class WebsiteSaleDashboardRenderer extends ListRenderer {
    static template = 'website_sale.ListRenderer';
    static components = {
        ...ListRenderer.components,
        WebsiteSaleDashboard,
    };
}

export const websiteSaleDashboardListView = {
    ...listView,
    Renderer: WebsiteSaleDashboardRenderer,
};

registry.category('views').add('website_sale_dashboard_list', websiteSaleDashboardListView);
