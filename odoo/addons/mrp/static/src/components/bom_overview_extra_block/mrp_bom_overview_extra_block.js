/** @odoo-module **/

import { useBus } from "@web/core/utils/hooks";
import { BomOverviewLine } from "../bom_overview_line/mrp_bom_overview_line";
import { BomOverviewSpecialLine } from "../bom_overview_special_line/mrp_bom_overview_special_line";
import { Component, onWillUnmount, onWillUpdateProps, useState } from "@odoo/owl";

export class BomOverviewExtraBlock extends Component {
    setup() {
        this.state = useState({
            isFolded: !this.props.unfoldAll,
        });
        if (this.props.unfoldAll) {
            this.props.changeFolded({ ids: [this.identifier], isFolded: false });
        }

        useBus(this.env.overviewBus, "unfold-all", () => this._unfold());

        onWillUpdateProps(newProps => {
            if (this.props.data.product_id != newProps.data.product_id) {
                this.state.isFolded = true;
            }
        });

        onWillUnmount(() => {
            // Need to notify main component that the block was folded so it doesn't appear on the PDF.
            this.props.changeFolded({ ids: [this.identifier], isFolded: true });
        });
    }

    //---- Handlers ----

    onToggleFolded() {
        const newState = !this.state.isFolded;
        this.state.isFolded = newState;
        this.props.changeFolded({ ids: [this.identifier], isFolded: newState });
    }

    _unfold() {
        this.state.isFolded = false;
        this.props.changeFolded({ ids: [this.identifier], isFolded: false })
    }

    //---- Getters ----

    get identifier() {
        return `${this.props.type}_${this.props.data.index}`;
    }
}

BomOverviewExtraBlock.template = "mrp.BomOverviewExtraBlock";
BomOverviewExtraBlock.components = {
    BomOverviewLine,
    BomOverviewSpecialLine,
};
BomOverviewExtraBlock.props = {
    unfoldAll: { type: Boolean, optional: true },
    type: {
        type: String,
        validate: t => ["operations", "byproducts"].includes(t),
    },
    showOptions: Object,
    data: Object,
    precision: Number,
    changeFolded: Function,
};
BomOverviewExtraBlock.defaultProps = {
    showAvailabilities: false,
    showCosts: false,
    extraColumnCount: 0,
};
