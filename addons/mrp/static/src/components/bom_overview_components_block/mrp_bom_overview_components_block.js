/** @odoo-module **/

import { useBus } from "@web/core/utils/hooks";
import { BomOverviewLine } from "../bom_overview_line/mrp_bom_overview_line";
import { BomOverviewExtraBlock } from "../bom_overview_extra_block/mrp_bom_overview_extra_block";
import { Component, onWillUnmount, onWillUpdateProps, useState } from "@odoo/owl";

export class BomOverviewComponentsBlock extends Component {
    static template = "mrp.BomOverviewComponentsBlock";
    static components = {
        BomOverviewLine,
        BomOverviewComponentsBlock,
        BomOverviewExtraBlock,
    };
    static props = {
        unfoldAll: { type: Boolean, optional: true },
        showOptions: Object,
        currentWarehouseId: { type: Number, optional: true },
        data: Object,
        precision: Number,
        changeFolded: Function,
        getChildBomData: Function,
    };
    static defaultProps = {
        unfoldAll: false,
    };

    setup() {
        const childFoldstate = this.childIds.reduce((prev, curr) => ({ ...prev, [curr]: !this.props.unfoldAll}), {});
        this.state = useState({
            ...childFoldstate,
            unfoldAll: this.props.unfoldAll || false,
            isLoading: [],
        });
        if (this.props.unfoldAll) {
            this.props.changeFolded({ ids: this.childIds, isFolded: false });
        }

        if (this.hasComponents) {
            useBus(this.env.overviewBus, "unfold-all", () => this._unfoldAll());
        }

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
                this.props.changeFolded({ ids: this.childIds, isFolded: true });
            }
        });
    }
    //---- Handlers ----

    async onToggleFolded(foldId) {
        const newState = !this.state[foldId];
        if (!newState) {
            const cleanedFoldId =
                foldId.search("component_") >= 0 ? foldId.substring(10) : foldId.substring(4);
            const element = this.props.data.components.find(
                (component) => component.index == cleanedFoldId
            );
            if (element && !element["fetched"]) {
                this.state.isLoading.push(cleanedFoldId);
                await this.props.getChildBomData(
                    cleanedFoldId,
                    element.bom_id,
                    element.quantity,
                    element.product_id,
                    cleanedFoldId.split("/").length - 1
                );
                this.state.isLoading = this.state.isLoading.filter(function (e) {
                    return e !== cleanedFoldId;
                });
            }
        }

        this.state[foldId] = newState;
        this.state.unfoldAll = false;
        this.props.changeFolded({ ids: [foldId], isFolded: newState });
    }

    _unfoldAll() {
        const allChildIds = this.childIds;
        this.state.unfoldAll = true;
        allChildIds.forEach(id => this.state[id] = false);
        this.props.changeFolded({ ids: allChildIds, isFolded: false });
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
