import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { formatFloat, formatFloatTime } from "@web/views/fields/formatters";

export class ProjectProfitabilitySection extends Component {

    static props = {
        revenue: Object,
        labels: Object,
        formatMonetary: Function,
        onProjectActionClick: Function,
        onClick: Function,
        projectId: Number,
        context: Object,
    };
    static template = "sale_project.ProjectProfitabilitySection";


    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            isFolded: true,
            displayLoadMore: null,
        });
        this.sale_items = [];
    }

    get revenue() {
        return this.props.revenue;
    }

    async toggleSaleItems() {
        if (this.state.displayLoadMore === null) {
            // first time the section is unfold, load the 5 first items.
            await this.onLoadMoreClick()
        }
        // the state change is done at the end to ensure the loaded data are present when the component is rendered
        this.state.isFolded = !this.state.isFolded;
    }

    formatValue(value, unit) {
        return unit === "Hours" ? formatFloatTime(value) : formatFloat(value);
    }

    _getOrmValue(offset, section_id) {
        return {
            function: "get_sale_items_data",
            args: [this.props.projectId, offset, 5, true, section_id],
        };
    }

    async onLoadMoreClick() {
        const offset = this.sale_items.length;
        const orm_value = this._getOrmValue(offset, this.props.revenue.id);
        const newItems = await this.orm.call(
            "project.project",
            orm_value.function,
            orm_value.args,
            {
                context: this.props.context,
            }
        );
        this.sale_items = [...this.sale_items, ...newItems.sol_items];
        this.state.displayLoadMore = newItems.displayLoadMore;
        this.render();
    }

    async onSaleItemActionClick(params) {
        if (params.resId && params.type !== "object") {
            const action = await this.actionService.loadAction(params.name, this.props.context);
            this.actionService.doAction({
                ...action,
                res_id: params.resId,
                views: [[false, "form"]],
            });
        } else {
            this.props.onProjectActionClick(params);
        }
    }
}
