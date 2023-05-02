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
    static template = "mrp.MoOverview";

    setup() {
        this.actionService = useService("action");
        this.ormService = useService("orm");
        this.unfoldedIds = new Set();
        this.context = {};

        this.state = useState({
            data: {},
            isDone: false,
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
        this.state.isDone = ['done', 'cancel'].some(doneState => reportValues.data?.summary?.state === doneState);
        if (this.state.isDone) {
            // Hide Availabilities / Receipts / Status columns when the MO is done.
            this.state.showOptions.availabilities = false;
            this.state.showOptions.receipts = false;
            this.state.showOptions.replenishments = false;
        }
        this.state.showOptions.uom = reportValues.context.show_uom;
        this.context = reportValues.context;
        if (reportValues.data?.operations?.summary?.index) {
            // Main MO's operations are always unfolded by default.
            this.unfoldedIds.add(reportValues.data.operations.summary.index);
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
        const reportName = `mrp.report_mo_overview?docids=${this.activeId}`
                         + `&replenishments=${+this.state.showOptions.replenishments}`
                         + `&availabilities=${+this.state.showOptions.availabilities}`
                         + `&receipts=${+this.state.showOptions.receipts}`
                         + `&moCosts=${+this.state.showOptions.moCosts}`
                         + `&productCosts=${+this.state.showOptions.productCosts}`
                         + `&unfoldedIds=${JSON.stringify(Array.from(this.unfoldedIds))}`;

        return this.actionService.doAction({
            type: "ir.actions.report",
            report_type: "qweb-pdf",
            report_name: reportName,
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
            moCosts: true,
            productCosts: true,
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

    get showMoCosts() {
        return this.state.showOptions.moCosts;
    }

    get showProductCosts() {
        return this.state.showOptions.productCosts;
    }
}

MoOverview.components = {
    Layout,
    MoOverviewLine,
    MoOverviewDisplayFilter,
    MoOverviewComponentsBlock,
};
MoOverview.props = {...standardActionServiceProps };

registry.category("actions").add("mrp_mo_overview", MoOverview);
