import { BomOverviewLine } from "../bom_overview_line/mrp_bom_overview_line";
import { BomOverviewSpecialLine } from "../bom_overview_special_line/mrp_bom_overview_special_line";
import { Component, onWillUnmount, proxy, t, useOnChange, usePlugin, useProps } from "@odoo/owl";
import { MrpOverviewPlugin } from "../mrp_overview_plugin";

export class BomOverviewExtraBlock extends Component {
    static template = "mrp.BomOverviewExtraBlock";
    static components = {
        BomOverviewLine,
        BomOverviewSpecialLine,
    };

    props = useProps({
        unfoldAll: t.boolean().optional(),
        type: t.selection(["operations", "byproducts"]),
        showOptions: t.object(),
        data: t.object(),
        precision: t.number(),
        changeFolded: t.function(),
    });

    setup() {
        this.overviewPlugin = usePlugin(MrpOverviewPlugin);
        this.state = proxy({
            isFolded: !this.props.unfoldAll,
        });
        if (this.props.unfoldAll) {
            this.props.changeFolded({ ids: [this.identifier], isFolded: false });
        }

        this.overviewPlugin.onToggleFoldAll((isFolded) => this._onToggleFoldAll(isFolded));

        useOnChange(
            () => [this.props.data.product_id],
            () => {
                this.state.isFolded = true;
                this.props.changeFolded({ ids: [this.identifier], isFolded: true });
            },
            { initialRun: false }
        );

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

    _onToggleFoldAll(isFolded) {
        this.state.isFolded = isFolded;
        this.props.changeFolded({ ids: [this.identifier], isFolded });
    }

    //---- Getters ----

    get identifier() {
        return `${this.props.type}_${this.props.data.index}`;
    }
}
