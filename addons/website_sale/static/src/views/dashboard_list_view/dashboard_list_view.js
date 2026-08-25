import { registry } from '@web/core/registry';
import { ListRenderer } from '@web/views/list/list_renderer';
import { SaleListView } from "@sale/views/sale_onboarding_list/sale_onboarding_list_view";
import { WebsiteSaleDashboard } from '../../js/dashboard/dashboard';

export class DashboardListRenderer extends ListRenderer {
	static template = 'website_sale.ListRenderer';
	static components = {
		...ListRenderer.components,
		WebsiteSaleDashboard,
	};
}

export const dashboardListView = {
	...SaleListView,
	Renderer: DashboardListRenderer,
};

registry.category('views').add('website_sale_dashboard_list', dashboardListView);
