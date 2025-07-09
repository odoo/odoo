import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, providePlugins, proxy, usePlugin, useProps } from "@odoo/owl";
import { MrpOverviewPlugin } from "../mrp_overview_plugin";
import { registry } from "@web/core/registry";
import { Layout } from "@web/search/layout";
import { standardActionServiceProps, ActionPlugin } from "@web/webclient/actions/action_plugin";
import { MoOverviewLine } from "../mo_overview_line/mrp_mo_overview_line";
import { MoOverviewDisplayFilter } from "../mo_overview_display_filter/mrp_mo_overview_display_filter";
import { MoOverviewComponentsBlock } from "../mo_overview_components_block/mrp_mo_overview_components_block";
import { formatMonetary } from "@web/views/fields/formatters";
import { ORM } from "@web/core/orm_plugin";

export class MoOverview extends Component {
    static components = {
        Layout,
        MoOverviewLine,
        MoOverviewDisplayFilter,
        MoOverviewComponentsBlock,
    };
    props = useProps(standardActionServiceProps);

    static template = "mrp.MoOverview";

    setup() {
        this.actionPlugin = usePlugin(ActionPlugin);
        this.ormPlugin = usePlugin(ORM);
        this.foldableIds = new Set();
        this.unfoldedIds = new Set();
        this.context = {};

        this.state = proxy({
            data: {},
            showOptions: this.getDefaultConfig(),
            foldable: true,
            allFolded: true,
        });

        providePlugins([MrpOverviewPlugin]);
        this.overviewPlugin = usePlugin(MrpOverviewPlugin);

        onWillStart(async () => {
            await this.getManufacturingData(true);
        });
        this.overviewPlugin.onUpdateFolded((foldInfo) => this.onChangeFolded(foldInfo));
        this.overviewPlugin.onReload(() => this.getManufacturingData());
    }

    async getManufacturingData(shouldInitializeFoldState = false) {
        const reportValues = await this.ormPlugin.call(
            "report.mrp.report_mo_overview",
            "get_report_values",
            [this.activeId],
        );
        this.state.data = reportValues.data;
        if (this.isProductionDone) {
            // Hide Availabilities / Receipts / Status columns when the MO is done.
            this.state.showOptions.availabilities = false;
            this.state.showOptions.receipts = false;
            this.state.showOptions.replenishments = false;
            this.state.showOptions.unitCosts = true;
        }
        this.state.showOptions.uom = reportValues.context.show_uom;
        this.context = reportValues.context;
        // Main MO's operations & byproducts are always unfolded by default.
        if (shouldInitializeFoldState) {
            if (this.hasOperations) {
                this.unfoldedIds.add(reportValues.data.operations.summary.index);
            }
            if (this.hasByproducts) {
                this.unfoldedIds.add(reportValues.data.byproducts.summary.index);
            }
        }
        this.getFoldableIds(reportValues.data);
        this.state.allFolded = this.unfoldedIds.size !== this.foldableIds.size;
        this.state.foldable = this.foldableIds.size > 0;
    }

    //---- Handlers ----

    onChangeDisplay(displayInfo) {
        this.state.showOptions[displayInfo] = !this.state.showOptions[displayInfo];
    }

    onChangeFolded(foldInfo) {
        const { indexes, isFolded } = foldInfo;
        const operation = isFolded ? "delete" : "add";
        indexes.forEach((index) => {
            if (this.foldableIds.has(index)) {
                this.unfoldedIds[operation](index);
            }
        });
        if (this.unfoldedIds.size === 0) {
            this.state.allFolded = true;
        } else if (this.unfoldedIds.size === this.foldableIds.size) {
            this.state.allFolded = false;
        }
    }

    async onPrint() {
        return this.actionPlugin.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: this.reportName,
        });
    }

    clickToggleFold() {
        this.overviewPlugin.toggleFoldAll(!this.state.allFolded);
    }

    //---- Helpers ----

    getDefaultConfig() {
        return {
            uom: false,
            toReplenish: false,
            replenishments: true,
            availabilities: true,
            receipts: true,
            unitCosts: false,
            moCosts: true,
        };
    }

    formatCost(cost) {
        return formatMonetary(cost, { currencyId: this.state.data.summary.currency_id });
    }

    getFoldableIds(data) {
        const children = [...(data.components ?? []), ...(data.replenishments ?? [])];
        const hasOperations = data.operations?.details?.length > 0;
        const hasByproducts = data.byproducts?.details?.length > 0;
        // The main MO has no index: it is always unfolded, so it is not foldable.
        if (data.summary.index && (children.length || hasOperations || hasByproducts)) {
            this.foldableIds.add(data.summary.index);
        }
        for (const child of children) {
            this.getFoldableIds(child);
        }
        if (hasOperations) {
            this.foldableIds.add(data.operations.summary.index);
        }
        if (hasByproducts) {
            this.foldableIds.add(data.byproducts.summary.index);
        }
    }

    //---- Getters ----

    get activeId() {
        return this.props.action.context.active_id;
    }

    get showUom() {
        return this.state.showOptions.uom;
    }

    get showReplenishments() {
        return this.state.showOptions.replenishments;
    }

    get showAvailabilities() {
        return this.state.showOptions.availabilities;
    }

    get showReceipts() {
        return this.state.showOptions.receipts;
    }

    get showUnitCosts() {
        return this.state.showOptions.unitCosts;
    }

    get showMoCosts() {
        return this.state.showOptions.moCosts;
    }

    get isProductionDone() {
        return this.state.data?.summary?.state === "done";
    }

    get isProductionCancelled() {
        return this.state.data?.summary?.state === "cancel";
    }

    get foldButtonText() {
        return this.state.allFolded ? _t("Unfold") : _t("Fold");
    }

    get hasOperations() {
        return this.state.data?.operations?.details?.length > 0;
    }

    get hasByproducts() {
        return this.state.data?.byproducts?.details?.length > 0;
    }

    get hasBreakdown() {
        return this.state.data?.cost_breakdown?.length > 0;
    }

    get totalColspan() {
        let colspan = 2; // Name & Quantity
        if (this.showReplenishments) {
            colspan++;
        }
        if (this.showAvailabilities) {
            colspan += 2; // Free to use / On Hand & Consumed
        }
        if (this.showUom) {
            colspan++;
        }
        if (this.showReceipts) {
            colspan++;
        }
        if (this.showUnitCosts) {
            colspan++;
        }
        return colspan;
    }

    get reportName() {
        return (
            `mrp.report_mo_overview?docids=${this.activeId}` +
            `&replenishments=${+this.state.showOptions.replenishments}` +
            `&availabilities=${+this.state.showOptions.availabilities}` +
            `&receipts=${+this.state.showOptions.receipts}` +
            `&unitCosts=${+this.state.showOptions.unitCosts}` +
            `&moCosts=${+this.state.showOptions.moCosts}` +
            `&unfoldedIds=${JSON.stringify(Array.from(this.unfoldedIds))}`
        );
    }
}

registry.category("actions").add("mrp_mo_overview", MoOverview);
