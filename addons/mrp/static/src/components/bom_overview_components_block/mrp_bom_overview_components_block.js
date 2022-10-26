/** @odoo-module **/

import { BomOverviewLine } from "../bom_overview_line/mrp_bom_overview_line";
import { BomOverviewExtraBlock } from "../bom_overview_extra_block/mrp_bom_overview_extra_block";

const { Component, onMounted, onWillUnmount, onWillUpdateProps, useState } = owl;

export class BomOverviewComponentsBlock extends Component {
    setup() {
        const childFoldstate = this.childIds.reduce((prev, curr) => ({ ...prev, [curr]: !this.props.unfoldAll}), {});
        this.state = useState({
            ...childFoldstate,
            unfoldAll: this.props.unfoldAll || false,
        });
        if (this.props.unfoldAll) {
            this.props.bus.trigger("change-fold", { ids: this.childIds, isFolded: false });
        }

        onMounted(() => {
            if (this.hasComponents) {
                this.props.bus.addEventListener(`toggle-fold-${this.identifier}`, (ev) => this._onToggleFolded(ev.detail));
                this.props.bus.addEventListener("unfold-all", () => this._unfoldAll());
            }
        });

        onWillUpdateProps(newProps => {
            if (this.data.product_id != newProps.data.product_id) {
                this.childIds.forEach(id => delete this.state[id]);
                const newChildIds = this.getHasComponents(newProps.data) ? newProps.data.components.map(c => this.getIdentifier(c)) : [];
                newChildIds.forEach(id => this.state[id] = true);
                this.state.unfoldAll = false;
            }
        });

        onWillUnmount(() => {
            if (this.hasComponents) {
                this.props.bus.trigger("change-fold", { ids: this.childIds, isFolded: true });
                this.props.bus.removeEventListener(`toggle-fold-${this.identifier}`, (ev) => this._onToggleFolded(ev.detail));
                this.props.bus.removeEventListener("unfold-all", () => this._unfoldAll());
            }
        });
    }
    //---- Handlers ----

    _onToggleFolded(foldId) {
        const newState = !this.state[foldId];
        this.state[foldId] = newState;
        this.state.unfoldAll = false;
        this.props.bus.trigger("change-fold", { ids: [foldId], isFolded: newState });
    }

    _unfoldAll() {
        const allChildIds = this.childIds;
        this.state.unfoldAll = true;
        allChildIds.forEach(id => this.state[id] = false);
        this.props.bus.trigger("change-fold", { ids: allChildIds, isFolded: false });
    }

    //---- Getters ----

    get data() {
        return this.props.data;
    }

    get hasComponents() {
        return this.getHasComponents(this.data);
    }

    get childIds() {
        return this.hasComponents ? this.data.components.map(c => this.getIdentifier(c)) : [];
    } 

    get identifier() {
        return this.getIdentifier(this.data);
    }

    get operationsId() {
        return this.getIdentifier(this.data, "operations");
    }

    get byproductsId() {
        return this.getIdentifier(this.data, "byproducts");
    }

    get showOperations() {
        return this.props.showOptions.operations;
    }

    //---- Utils ----

    getHasComponents(data) {
        return data.components && data.components.length > 0;
    }

    getIdentifier(data, type=null) {
        return `${type ? type : data.type}_${data.index}`;
    }
}

BomOverviewComponentsBlock.template = "mrp.BomOverviewComponentsBlock";
BomOverviewComponentsBlock.components = {
    BomOverviewLine,
    BomOverviewComponentsBlock,
    BomOverviewExtraBlock,
};
BomOverviewComponentsBlock.props = {
    bus: Object,
    unfoldAll: { type: Boolean, optional: true },
    showOptions: Object,
    currentWarehouseId: { type: Number, optional: true },
    data: Object,
};
BomOverviewComponentsBlock.defaultProps = {
    unfoldAll: false,
};
