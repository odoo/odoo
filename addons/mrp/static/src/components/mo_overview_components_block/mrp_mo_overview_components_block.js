import { Component, onWillUnmount, proxy, t, useOnChange, usePlugin, useProps } from "@odoo/owl";
import { MrpOverviewPlugin } from "../mrp_overview_plugin";
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
    props = useProps({
        unfoldAll: t.boolean().optional(false),
        summary: t.object().optional(),     // Used in an override in stock_account
        components: t.array().optional(),
        operations: t
            .object({
                summary: t.object(),
                details: t.array(),
            })
            .optional(),
        byproducts: t
            .object({
                summary: t.object(),
                details: t.array(),
            })
            .optional(),
        showOptions: SHOW_OPTIONS,
    });

    static template = "mrp.MoOverviewComponentsBlock";

    setup() {
        this.overviewPlugin = usePlugin(MrpOverviewPlugin);
        this.state = proxy({
            fold: this.getIndexStates(this.props),
            unfoldAll: this.props.unfoldAll,
        });

        if (this.props.unfoldAll) {
            this.overviewPlugin.updateFolded(Object.keys(this.state.fold), false);
        }

        this.overviewPlugin.onToggleFoldAll((isFolded) => this._onToggleFoldAll(isFolded));

        useOnChange(
            () => Object.keys(this.getIndexStates(this.props)),
            () => {
                // Update the fold indexes so it matches the newly added lines.
                this.state.fold = { ...this.getIndexStates(this.props), ...this.state.fold };
            },
            { initialRun: false }
        );

        onWillUnmount(() => this.overviewPlugin.updateFolded(Object.keys(this.state.fold), true));
    }

    //---- Handlers ----

    onToggleFolded(foldIndex) {
        this.state.unfoldAll = false;
        const isFolded = !this.state.fold[foldIndex];
        // Folding a line also folds its children.
        const indexes = isFolded
            ? Object.keys(this.state.fold).filter((key) => key.startsWith(foldIndex))
            : [foldIndex];
        indexes.forEach((index) => (this.state.fold[index] = isFolded));
        this.overviewPlugin.updateFolded(indexes, isFolded);
    }

    _onToggleFoldAll(isFolded) {
        this.state.unfoldAll = !isFolded;
        const foldIndexes = Object.keys(this.state.fold);
        foldIndexes.forEach((index) => (this.state.fold[index] = isFolded));
        this.overviewPlugin.updateFolded(foldIndexes, isFolded);
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
        return (
            replenishment?.components?.length > 0 ||
            replenishment?.operations?.details?.length > 0 ||
            replenishment?.byproducts?.details?.length > 0
        );
    }

    hasComponentsBlock(replenishment) {
        return this.hasComponents(replenishment) && !this.state.fold[replenishment?.summary.index];
    }

    filterComponentsToReplenish(components) {
        return components.flatMap((component) => {
            const replenishments = (component.replenishments ?? []).flatMap((replenishment) => {
                const nestedComponents = this.filterComponentsToReplenish(
                    replenishment.components ?? []
                );
                if (replenishment.summary?.model === "to_order" || nestedComponents.length) {
                    return [{ ...replenishment, components: nestedComponents }];
                }
                return [];
            });
            if (component.summary?.state === "to_order" || replenishments.length) {
                return [{ ...component, replenishments }];
            }
            return [];
        });
    }

    get components() {
        const components = this.props.components ?? [];
        if (this.props.showOptions.toReplenish) {
            return this.filterComponentsToReplenish(components);
        }
        return components;
    }
}
