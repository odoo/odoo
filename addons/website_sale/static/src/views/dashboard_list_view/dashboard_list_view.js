import { registry } from '@web/core/registry';
import { ListRenderer } from '@web/views/list/list_renderer';
import { DashboardListController } from '@sale/views/dashboard_list_view/dashboard_list_view';
import { saleListView } from '@sale/views/sale_onboarding_list/sale_onboarding_list_view';
import { WebsiteSaleDashboard } from '../../js/dashboard/dashboard';

export class DashboardListRenderer extends ListRenderer {
    static template = 'website_sale.ListRenderer';
    static components = {
        ...ListRenderer.components,
        WebsiteSaleDashboard,
    };
}

export class eCommerceDashboardListController extends DashboardListController {
    async afterExecuteActionButton(clickParams) {
        await super.afterExecuteActionButton(clickParams);
        this.env.bus.trigger("reload");
    }
}

export const dashboardListView = {
    ...saleListView,
    Renderer: DashboardListRenderer,
    Controller: eCommerceDashboardListController,
};

registry.category('views').add('website_sale_dashboard_list', dashboardListView);
