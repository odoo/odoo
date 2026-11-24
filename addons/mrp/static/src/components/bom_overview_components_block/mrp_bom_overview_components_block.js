import { BomOverviewLine } from "../bom_overview_line/mrp_bom_overview_line";
import { BomOverviewExtraBlock } from "../bom_overview_extra_block/mrp_bom_overview_extra_block";
import { Component, onWillUnmount, proxy, t, useOnChange, usePlugin, useProps } from "@odoo/owl";
import { MrpOverviewPlugin } from "../mrp_overview_plugin";

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
    });

    setup() {
        this.overviewPlugin = usePlugin(MrpOverviewPlugin);
        const childFoldstate = this.childIds.reduce((prev, curr) => ({ ...prev, [curr]: !this.props.unfoldAll}), {});
        this.state = proxy({
            ...childFoldstate,
            unfoldAll: this.props.unfoldAll,
        });
        if (this.props.unfoldAll) {
            this.overviewPlugin.updateFolded(this.childIds, false);
        }

        this.overviewPlugin.onToggleFoldAll((isFolded) => this._onToggleFoldAll(isFolded));

        useOnChange(
            () => [this.data.product_id],
            () => {
                const oldChildIds = Object.keys(this.state).filter((id) => id !== "unfoldAll");
                oldChildIds.forEach((id) => delete this.state[id]);
                this.childIds.forEach((id) => (this.state[id] = true));
                this.state.unfoldAll = false;
                this.overviewPlugin.updateFolded(oldChildIds, true);
            },
            { initialRun: false }
        );

        onWillUnmount(() => {
            if (this.hasComponents) {
                this.overviewPlugin.updateFolded(this.childIds, true);
            }
        });
    }
    //---- Handlers ----

    onToggleFolded(foldId) {
        const newState = !this.state[foldId];
        this.state[foldId] = newState;
        this.state.unfoldAll = false;
        this.overviewPlugin.updateFolded([foldId], newState);
    }

    _onToggleFoldAll(isFolded) {
        const allChildIds = this.childIds;
        this.state.unfoldAll = !isFolded;
        allChildIds.forEach((id) => (this.state[id] = isFolded));
        this.overviewPlugin.updateFolded(allChildIds, isFolded);
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
