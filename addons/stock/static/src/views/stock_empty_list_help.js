import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { render } from "@web/owl2/utils";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";
import { useActionLinks } from "@web/views/view_hook";

export class StockActionHelper extends Component {
    static template = "stock.StockActionHelper";
    static props = ["noContentHelp"];
    setup() {
        this.handler = useActionLinks(this.env.searchModel?.resModel, () => render(this));
    }
}

export class StockListRenderer extends ListRenderer {
    static template = "stock.StockListRenderer";
    static components = {
        ...StockListRenderer.components,
        StockActionHelper,
    };
}

export const StockListView = {
    ...listView,
    Renderer: StockListRenderer,
};

registry.category("views").add("stock_list_view", StockListView);
