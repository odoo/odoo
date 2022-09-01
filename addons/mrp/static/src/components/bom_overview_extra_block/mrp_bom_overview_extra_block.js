/** @odoo-module **/

import { BomOverviewLine } from "../bom_overview_line/mrp_bom_overview_line";
import { BomOverviewSpecialLine } from "../bom_overview_special_line/mrp_bom_overview_special_line";

const { Component, onMounted, onWillUnmount, onWillUpdateProps, useState } = owl;

export class BomOverviewExtraBlock extends Component {
    setup() {
        this.state = useState({
            isFolded: !this.props.unfoldAll,
        });
        if (this.props.unfoldAll) {
            this.props.bus.trigger("change-fold", { ids: [this.identifier], isFolded: false });
        }

        onMounted(() => {
            this.props.bus.addEventListener(`toggle-fold-${this.identifier}`, () => this._onToggleFolded());
            this.props.bus.addEventListener("unfold-all", () => this._unfold());
        });

        onWillUpdateProps(newProps => {
            if (this.props.data.product_id != newProps.data.product_id) {
                this.state.isFolded = true;
            }
        });

        onWillUnmount(() => {
            this.props.bus.trigger("change-fold", { ids: [this.identifier], isFolded: true });
            this.props.bus.removeEventListener(`toggle-fold-${this.identifier}`, () => this._onToggleFolded());
            this.props.bus.removeEventListener("unfold-all", () => this._unfold());
        });
    }

    //---- Handlers ----

    _onToggleFolded() {
        const newState = !this.state.isFolded;
        this.state.isFolded = newState;
        this.props.bus.trigger("change-fold", { ids: [this.identifier], isFolded: newState });
    }

    _unfold() {
        this.state.isFolded = false;
        this.props.bus.trigger("change-fold", { ids: [this.identifier], isFolded: false });
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
    bus: Object,
    unfoldAll: { type: Boolean, optional: true },
    type: {
        type: String,
        validate: t => ["operations", "byproducts"].includes(t),
    },
    showOptions: Object,
    data: Object,
};
BomOverviewExtraBlock.defaultProps = {
    showAvailabilities: false,
    showCosts: false,
    extraColumnCount: 0,
};
