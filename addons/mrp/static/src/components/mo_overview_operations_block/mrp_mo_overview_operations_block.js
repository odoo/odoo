import { Component, props, proxy, t } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { formatFloatTime, formatMonetary } from "@web/views/fields/formatters";
import { MoOverviewLine } from "../mo_overview_line/mrp_mo_overview_line";
import { SHOW_OPTIONS } from "../mo_overview_display_filter/mrp_mo_overview_display_filter";

export const MO_OVERVIEW_SUMMARY_SHAPE = {
    index: t.string(),
    quantity: t.number().optional(),
    quantity_decorator: t.or([t.string(), t.boolean()]).optional(),
    mo_cost: t.number().optional(),
    mo_cost_decorator: t.or([t.string(), t.boolean()]).optional(),
    bom_cost: t.or([t.number(), t.boolean()]).optional(),
    real_cost: t.number().optional(),
    real_cost_decorator: t.or([t.string(), t.boolean()]).optional(),
    uom_name: t.string().optional(),
    currency_id: t.number().optional(),
    currency: t.string().optional(),
    done: t.boolean().optional(),
};

export const moOverviewOperationsBlockProps = {
    unfoldAll: t.boolean().optional(false),
    operations: t.array(),
    summary: t.object(MO_OVERVIEW_SUMMARY_SHAPE),
    showOptions: SHOW_OPTIONS,
};

export class MoOverviewOperationsBlock extends Component {
    static template = "mrp.MoOverviewOperationsBlock";
    static components = {
        MoOverviewLine,
    };
    props = props(moOverviewOperationsBlockProps);

    setup() {
        this.formatFloatTime = formatFloatTime;
        this.state = proxy({
            // Unfold the main MO's operations by default
            isFolded: this.level > 0 && !this.props.unfoldAll,
        });
        if (this.props.unfoldAll) {
            this.env.overviewBus.trigger("update-folded", { indexes: [this.index], isFolded: false });
        }

        useBus(this.env.overviewBus, "toggle-fold-all-mo", (ev) =>
            this._onFoldAll(ev.detail.foldAll)
        );
    }

    //---- Handlers ----

    toggleFolded() {
        this.state.isFolded = !this.state.isFolded;
        this.env.overviewBus.trigger("update-folded", { indexes: [this.index], isFolded: this.state.isFolded });
    }

    _onFoldAll(foldAll) {
        this.state.isFolded = foldAll;
        this.env.overviewBus.trigger("update-folded", { indexes: [this.index], isFolded: foldAll });
    }

    //---- Helpers ----

    formatMonetary(val) {
        return formatMonetary(val, { currencyId: this.props.summary.currency_id });
    }

    getColorClass(decorator) {
        return decorator ? `text-${decorator}` : "";
    }

    //---- Getters ----

    get hasOperations() {
        return this.props?.operations?.length > 0;
    }

    get level() {
        return this.hasOperations ? this.props.operations[0].level - 1 : 0;
    }

    get index() {
        return this.props.summary.index;
    }

    get totalQuantity() {
        // Float for Hours when displaying done productions, FloatTime for Minutes otherwise.
        return this.props.summary?.done ?
            formatFloatTime(this.props.summary.quantity, { unit: "hours", showSeconds: true }) :
            formatFloatTime(this.props.summary.quantity, { unit: "minutes", showSeconds: true })
    }
}
