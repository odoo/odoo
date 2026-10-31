import { registry } from '@web/core/registry';
import { ListRenderer } from '@web/views/list/list_renderer';
import { ListController } from "@web/views/list/list_controller";
import { listView } from '@web/views/list/list_view';
import { WebsiteSaleDashboard } from '../../js/dashboard/dashboard';

export class DashboardListRenderer extends ListRenderer {
	static template = 'website_sale.ListRenderer';
	static components = {
		...ListRenderer.components,
		WebsiteSaleDashboard,
	};
}

export class DashboardListController extends ListController {
    get actionMenuProps() {
        const actionMenuProps = super.actionMenuProps;
        return {
            ...actionMenuProps,
            onActionExecuted: ({ noReload } = {}) => {
                actionMenuProps.onActionExecuted({ noReload });
                if (!noReload) {
                    this.env.bus.trigger("reload");
                }
            },
        };
    }

    async afterExecuteActionButton(clickParams) {
        await super.afterExecuteActionButton(clickParams);
        this.env.bus.trigger("reload");
    }
}

export const dashboardListView = {
	...listView,
	Renderer: DashboardListRenderer,
	Controller: DashboardListController,
};

registry.category('views').add('website_sale_dashboard_list', dashboardListView);
