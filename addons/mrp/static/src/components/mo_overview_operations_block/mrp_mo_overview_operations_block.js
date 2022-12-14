/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { formatFloatTime, formatMonetary } from "@web/views/fields/formatters";
import { MoOverviewLine } from "../mo_overview_line/mrp_mo_overview_line";

export class MoOverviewOperationsBlock extends Component {
    static template = "mrp.MoOverviewOperationsBlock";

    setup() {
        this.formatFloatTime = formatFloatTime;
        this.state = useState({
            // Unfold the main MO's operations by default
            isFolded: this.level > 0 && !this.props.unfoldAll,
        });
        if (this.props.unfoldAll) {
            this.env.overviewBus.trigger("update-folded", { indexes: [this.index], isFolded: false });
        }

        useBus(this.env.overviewBus, "unfold-all", () => this.unfold());
    }

    //---- Handlers ----

    toggleFolded() {
        this.state.isFolded = !this.state.isFolded;
        this.env.overviewBus.trigger("update-folded", { indexes: [this.index], isFolded: this.state.isFolded });
    }

    unfold() {
        this.state.isFolded = false;
        this.env.overviewBus.trigger("update-folded", { indexes: [this.index], isFolded: false });
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
}

MoOverviewOperationsBlock.components = {
    MoOverviewLine,
};
MoOverviewOperationsBlock.props = {
    unfoldAll: { type: Boolean, optional: true },
    operations: Array,
    summary: {
        type: Object,
        shape: {
            index: String,
            quantity: { type: Number, optional: true },
            quantity_decorator: { type: [String, Boolean], optional: true },
            mo_cost: { type: Number, optional: true },
            mo_cost_decorator: { type: [String, Boolean], optional: true },
            uom_name: { type: String, optional: true },
            currency_id: { type: Number, optional: true },
            currency: { type: String, optional: true },
        },
    },
    showOptions: {
        type: Object,
        shape: {
            uom: Boolean,
            replenishments: Boolean,
            availabilities: Boolean,
            receipts: Boolean,
            moCosts: Boolean,
            productCosts: Boolean,
        },
    },
};
MoOverviewOperationsBlock.defaultProps = {
    unfoldAll: false,
};
