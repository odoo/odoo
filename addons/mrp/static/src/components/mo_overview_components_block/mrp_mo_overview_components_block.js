import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { MoOverviewLine } from "../mo_overview_line/mrp_mo_overview_line";
import { MoOverviewOperationsBlock } from "../mo_overview_operations_block/mrp_mo_overview_operations_block";
import { MoOverviewByproductsBlock } from "../mo_overview_byproducts_block/mrp_mo_overview_byproducts_block";
import { SHOW_OPTIONS } from "../mo_overview_display_filter/mrp_mo_overview_display_filter";

export class MoOverviewComponentsBlock extends Component {
    static components = {
        MoOverviewLine,
        MoOverviewOperationsBlock,
        MoOverviewByproductsBlock,
        MoOverviewComponentsBlock,
    };
    static props = {
        unfoldAll: { type: Boolean, optional: true },
        components: { type: Array, optional: true },
        operations: {
            type: Object,
            shape: {
                summary: Object,
                details: Array,
            },
            optional: true,
        },
        byproducts: {
            type: Object,
            shape: {
                summary: Object,
                details: Array,
            },
            optional: true,
        },
        showOptions: SHOW_OPTIONS,
    };
    static defaultProps = {
        unfoldAll: false,
    };

    static template = "mrp.MoOverviewComponentsBlock";

    setup() {
        this.state = useState({
            fold: this.getIndexStates(this.props),
            unfoldAll: this.props.unfoldAll || false,
        });

        if (this.props.unfoldAll) {
            this.env.overviewBus.trigger("update-folded", { indexes: Object.keys(this.state.fold), isFolded: false });
        }

        useBus(this.env.overviewBus, "unfold-all", () => this.unfoldAll());

        onWillUpdateProps(newProps => {
            // Update the fold indexes so it matches the newly added lines.
            this.state.fold = { ...this.getIndexStates(newProps), ...this.state.fold };
        });
    }

    //---- Handlers ----

    onToggleFolded(foldIndex) {
        this.state.unfoldAll = false;
        const newState = !this.state.fold[foldIndex];
        if (newState) {
            // If a line is folded, its children lines must be folded as well
            Object.keys(this.state.fold).filter(key => key.startsWith(foldIndex)).forEach(index => {
                this.state.fold[index] = newState;
            });
        }
        this.state.fold[foldIndex] = newState;
        this.env.overviewBus.trigger("update-folded", { indexes: [foldIndex], isFolded: newState });
    }

    unfoldAll() {
        this.state.unfoldAll = true;
        const foldIndexes = Object.keys(this.state.fold);
        foldIndexes.forEach(index => this.state.fold[index] = false);
        this.env.overviewBus.trigger("update-folded", { indexes: foldIndexes, isFolded: false });
    }

    //---- Helpers ----

    getIndexStates(props) {
        const indexStates = {};
        (props?.components ?? []).forEach(component => {
            indexStates[component?.summary.index] = !props.unfoldAll;
            (component?.replenishments ?? []).forEach(replenishment => {
                indexStates[replenishment?.summary.index] = !props.unfoldAll;
            });
        });
        return indexStates;
    }

    hasReplenishments(component) {
        return component?.replenishments?.length > 0;
    }

    hasReplenishmentsBlock(component) {
        return this.hasReplenishments(component) && !this.state.fold[component?.summary.index];
    }

    hasComponents(replenishment) {
        return replenishment?.components?.length > 0 || replenishment?.operations?.details?.length > 0;
    }

    hasComponentsBlock(replenishment) {
        return this.hasComponents(replenishment) && !this.state.fold[replenishment?.summary.index];
    }
}
