import { registry } from '@web/core/registry';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { Dashboard } from '../../js/dashboard/dashboard';

export class DashboardKanbanRenderer extends KanbanRenderer {
	static template = 'website_sale.KanbanRenderer';
	static components = {
		...KanbanRenderer.components,
		Dashboard,
	};
}

export const dashboardKanbanView = {
	...kanbanView,
	Renderer: DashboardKanbanRenderer,
};

registry.category('views').add('website_sale_dashboard_kanban', dashboardKanbanView);
