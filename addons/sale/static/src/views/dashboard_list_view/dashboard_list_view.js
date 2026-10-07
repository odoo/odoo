import { registry } from '@web/core/registry';
import { ListRenderer } from '@web/views/list/list_renderer';
import { saleOrderListView } from '../sale_order_list/sale_order_list_view';
import { SaleOrderListController } from '../sale_order_list/sale_order_list_controller';
import { Dashboard } from '../../js/dashboard/dashboard';

export class DashboardListRenderer extends ListRenderer {
    static template = 'sale.ListRenderer';
    static components = {
        ...ListRenderer.components,
        Dashboard,
    };
}

export class DashboardListController extends SaleOrderListController {
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
}

export const dashboardListView = Object.assign(Object.create(saleOrderListView), {
    Controller: DashboardListController,
    Renderer: DashboardListRenderer,
});

registry.category('views').add('sale_dashboard_list', dashboardListView);
