import { registry } from '@web/core/registry';
import { ListRenderer } from '@web/views/list/list_renderer';
import { ListController } from "@web/views/list/list_controller";
import { listView } from '@web/views/list/list_view';
import { Dashboard } from '../../js/dashboard/dashboard';

export class DashboardListRenderer extends ListRenderer {
	static template = 'website_sale.ListRenderer';
	static components = {
		...ListRenderer.components,
		Dashboard,
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
                    this.model.bus.trigger("reload_ecommerce_dashboard");
                }
            },
        };
    }

    async afterExecuteActionButton(clickParams) {
        await super.afterExecuteActionButton(clickParams);
        this.model.bus.trigger("reload_ecommerce_dashboard");
    }
}

export const dashboardListView = {
	...listView,
	Renderer: DashboardListRenderer,
	Controller: DashboardListController,
};

registry.category('views').add('website_sale_dashboard_list', dashboardListView);
