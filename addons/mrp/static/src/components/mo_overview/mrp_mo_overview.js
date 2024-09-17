/** @odoo-module **/

import { Component, EventBus, onWillStart, useSubEnv, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { Layout } from "@web/search/layout";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { MoOverviewLine } from "../mo_overview_line/mrp_mo_overview_line";
import { MoOverviewDisplayFilter } from "../mo_overview_display_filter/mrp_mo_overview_display_filter";
import { MoOverviewComponentsBlock } from "../mo_overview_components_block/mrp_mo_overview_components_block";
import { formatMonetary } from "@web/views/fields/formatters";

export class MoOverview extends Component {
    static components = {
        Layout,
        MoOverviewLine,
        MoOverviewDisplayFilter,
        MoOverviewComponentsBlock,
    };
    static props = { ...standardActionServiceProps };

    static template = "mrp.MoOverview";

    setup() {
        this.actionService = useService("action");
        this.ormService = useService("orm");
        this.unfoldedIds = new Set();
        this.context = {};

        this.state = useState({
            data: {},
            showOptions: this.getDefaultConfig(),
        });

        useSubEnv({ overviewBus: new EventBus() });

        onWillStart(async () => {
            await this.getManufacturingData();
        });
        useBus(this.env.overviewBus, "update-folded", (ev) => this.onChangeFolded(ev.detail));
        useBus(this.env.overviewBus, "reload", () => this.getManufacturingData());
    }

    async getManufacturingData() {
        const reportValues = await this.ormService.call(
            "report.mrp.report_mo_overview",
            "get_report_values",
            [this.activeId],
        );
        this.state.data = reportValues.data;
        if (this.isProductionStarted) {
            this.state.showOptions.bomCosts = false;
        } else {
            this.state.showOptions.realCosts = false;
        }
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
        if (reportValues.data?.operations?.summary?.index) {
            this.unfoldedIds.add(reportValues.data.operations.summary.index);
        }
        if (reportValues.data?.byproducts?.summary?.index) {
            this.unfoldedIds.add(reportValues.data.byproducts.summary.index);
        }
    }

    //---- Handlers ----

    onChangeDisplay(displayInfo) {
        this.state.showOptions[displayInfo] = !this.state.showOptions[displayInfo];
    }

    onChangeFolded(foldInfo) {
        const { indexes, isFolded } = foldInfo;
        const operation = isFolded ? "delete" : "add";
        indexes.forEach(index => this.unfoldedIds[operation](index));
    }

    async onPrint() {
        return this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: this.reportName,
            report_file: "mrp.report_mo_overview",
        });
    }

    onUnfold() {
        this.env.overviewBus.trigger("unfold-all")
    }

    //---- Helpers ----

    getDefaultConfig() {
        return {
            uom: false,
            replenishments: true,
            availabilities: true,
            receipts: true,
            unitCosts: false,
            moCosts: true,
            bomCosts: true,
            realCosts: true,
        };
    }

    getColorClass(decorator) {
        return decorator ? `text-${decorator}` : "";
    }

    formatCost(cost) {
        return formatMonetary(cost, { currencyId: this.state.data.summary.currency_id });
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

    get showBomCosts() {
        return this.state.showOptions.bomCosts;
    }

    get showRealCosts() {
        return this.state.showOptions.realCosts;
    }

    get hasBom() {
        return this.state.data?.summary?.has_bom;
    }

    get isProductionStarted() {
        return !["draft", "confirmed"].includes(this.state.data?.summary?.state);
    }

    get isProductionDraft() {
        return this.state.data?.summary?.state === "draft";
    }

    get isProductionDone() {
        return this.state.data?.summary?.state === "done";
    }

    get hasOperations() {
        return this.state.data?.operations?.details?.length > 0;
    }

    get hasBreakdown() {
        return this.state.data?.cost_breakdown?.length > 0;
    }

    get totalColspan() {
        let colspan = 2;  // Name & Quantity
        if (this.showReplenishments) colspan++;
        if (this.showAvailabilities) colspan += 2;  // Free to use / On Hand & Reserved
        if (this.showUom) colspan++;
        if (this.showReceipts) colspan++;
        if (this.showUnitCosts) colspan++;
        return colspan;
    }

    get reportName() {
        return `mrp.report_mo_overview?docids=${this.activeId}`
            + `&replenishments=${+this.state.showOptions.replenishments}`
            + `&availabilities=${+this.state.showOptions.availabilities}`
            + `&receipts=${+this.state.showOptions.receipts}`
            + `&unitCosts=${+this.state.showOptions.unitCosts}`
            + `&moCosts=${+this.state.showOptions.moCosts}`
            + `&bomCosts=${+this.state.showOptions.bomCosts}`
            + `&realCosts=${+this.state.showOptions.realCosts}`
            + `&unfoldedIds=${JSON.stringify(Array.from(this.unfoldedIds))}`;
    }
}

registry.category("actions").add("mrp_mo_overview", MoOverview);
