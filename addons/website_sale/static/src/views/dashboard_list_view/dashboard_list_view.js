import { registry } from '@web/core/registry';
import { ListRenderer } from '@web/views/list/list_renderer';
import { listView } from '@web/views/list/list_view';
import { Dashboard } from '../../js/dashboard/dashboard';

export class DashboardListRenderer extends ListRenderer {
	static template = 'website_sale.ListRenderer';
	static components = {
		...ListRenderer.components,
		Dashboard,
	};
}

export const dashboardListView = {
	...listView,
	Renderer: DashboardListRenderer,
};

registry.category('views').add('website_sale_dashboard_list', dashboardListView);
