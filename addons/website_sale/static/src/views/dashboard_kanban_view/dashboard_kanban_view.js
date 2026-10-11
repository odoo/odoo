import { registry } from '@web/core/registry';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { WebsiteSaleDashboard } from '../../js/dashboard/dashboard';
import { saleKanbanView } from '@sale/views/sale_onboarding_kanban/sale_onboarding_kanban_view';

export class DashboardKanbanRenderer extends KanbanRenderer {
	static template = 'website_sale.KanbanRenderer';
	static components = {
		...KanbanRenderer.components,
		WebsiteSaleDashboard,
	};
}

export const dashboardKanbanView = {
	...saleKanbanView,
	Renderer: DashboardKanbanRenderer,
};

registry.category('views').add('website_sale_dashboard_kanban', dashboardKanbanView);
