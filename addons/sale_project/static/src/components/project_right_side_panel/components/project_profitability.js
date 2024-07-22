import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { ProjectProfitability } from "@project/components/project_right_side_panel/components/project_profitability";
import { formatFloat, formatFloatTime } from "@web/views/fields/formatters";

patch(ProjectProfitability.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");
    },

    toggleSaleItems(section) {
        section.isFolded = !section.isFolded;
    },

    _getOrmValue(offset, section) {
        return {
            function: "get_sale_items_data",
            args: [this.props.projectId, offset, 5, true, section.id],
        };
    },

    async onLoadMoreClick(section) {
        const offset = section.sale_items.length;
        const orm_value = this._getOrmValue(offset, section);
        const newItems = await this.orm.call(
            "project.project",
            orm_value.function,
            orm_value.args,
            {
                context: this.props.context,
            }
        );
        if (newItems.length < 5) {
            section.displayLoadMore = false;
        }
        section.sale_items = [...section.sale_items, ...newItems];
    },

    formatValue(value, unit) {
        return unit === "Hours" ? formatFloatTime(value) : formatFloat(value);
    },

    //---------------------------------------------------------------------
    // Handlers
    //---------------------------------------------------------------------

    /**
     * @private
     * @param {Object} params
     */
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
    },
});

patch(ProjectProfitability, {
    props: {
        ...ProjectProfitability.props,
        projectId: Number,
        context: Object,
    },
});
