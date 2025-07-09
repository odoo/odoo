import { useBus } from "@web/core/utils/hooks";
import { BomOverviewLine } from "../bom_overview_line/mrp_bom_overview_line";
import { BomOverviewExtraBlock } from "../bom_overview_extra_block/mrp_bom_overview_extra_block";
import { Component, onWillUnmount, onWillUpdateProps, useProps, proxy, t } from "@odoo/owl";

export class BomOverviewComponentsBlock extends Component {
    static template = "mrp.BomOverviewComponentsBlock";
    static components = {
        BomOverviewLine,
        BomOverviewComponentsBlock,
        BomOverviewExtraBlock,
    };
    props = useProps({
        unfoldAll: t.boolean().optional(false),
        showOptions: t.object(),
        currentWarehouseId: t.number().optional(),
        data: t.object(),
        precision: t.number(),
        changeFolded: t.function(),
    });

    setup() {
        const childFoldstate = this.childIds.reduce((prev, curr) => ({ ...prev, [curr]: !this.props.unfoldAll}), {});
        this.state = proxy({
            ...childFoldstate,
            unfoldAll: this.props.unfoldAll,
        });
        if (this.props.unfoldAll) {
            this.props.changeFolded({ ids: this.childIds, isFolded: false });
        }

        useBus(this.env.overviewBus, "toggle-fold-all", (ev) =>
            this._onToggleFoldAll(ev.detail.isFolded)
        );

        onWillUpdateProps(newProps => {
            if (this.data.product_id != newProps.data.product_id) {
                const oldChildIds = this.childIds;
                oldChildIds.forEach((id) => delete this.state[id]);
                const newChildIds = this.getHasComponents(newProps.data) ? newProps.data.components.map(c => this.getIdentifier(c)) : [];
                newChildIds.forEach(id => this.state[id] = true);
                this.state.unfoldAll = false;
                this.props.changeFolded({ ids: oldChildIds, isFolded: true });
            }
        });

        onWillUnmount(() => {
            if (this.hasComponents) {
                this.props.changeFolded({ ids: this.childIds, isFolded: true });
            }
        });
    }
    //---- Handlers ----

    onToggleFolded(foldId) {
        const newState = !this.state[foldId];
        this.state[foldId] = newState;
        this.state.unfoldAll = false;
        this.props.changeFolded({ ids: [foldId], isFolded: newState });
    }

    _onToggleFoldAll(isFolded) {
        const allChildIds = this.childIds;
        this.state.unfoldAll = !isFolded;
        allChildIds.forEach((id) => (this.state[id] = isFolded));
        this.props.changeFolded({ ids: allChildIds, isFolded });
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

    //---- Utils ----

    getHasComponents(data) {
        return data.components && data.components.length > 0;
    }

    getIdentifier(data, type=null) {
        return `${type ? type : data.type}_${data.index}`;
    }
}
