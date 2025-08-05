import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { Component, onWillStart, useChildSubEnv, useState } from "@odoo/owl";

import { StockValuationReportButtonsBar } from "../stock_valuation/buttons_bar/buttons_bar"
import { StockValuationReportController } from "../stock_valuation/controller"
import { StockValuationReportFilters } from "../stock_valuation/filters/filters"
import { StockValuationReportLine } from "../stock_valuation/line/line"
import { StockValuationReportToggleLine } from "../stock_valuation/line/toggle_line"


export class StockValuationReport extends Component {
    static template = "stock_account.StockValuationReport";
    static props = { ...standardActionServiceProps };
    static components = {
        ControlPanel,
        StockValuationReportButtonsBar,
        StockValuationReportFilters,
        StockValuationReportLine,
        StockValuationReportToggleLine,
    };

    setup() {
        this.controller = useState(new StockValuationReportController(this.props.action));
        this.state = useState({
            displayInventoryValuationLine: false,
        })
        this.orm = useService("orm");
        this.actionService = useService("action");
        this._t = _t;

        onWillStart(async () => {
            await this.controller.load(this.data);
        })

        useChildSubEnv({
            _t,
            controller: this.controller,
            formatMonetary: this.formatMonetary.bind(this),
        });
    }

    formatMonetary(value) {
        return formatMonetary(value, {
            currencyId: this.data.currency_id,
        });
    }

    get accrual() {
        return { label: _t("Accrual"), lines: [], value: 0 };
    }

    // Getters -----------------------------------------------------------------
    get data() {
        return this.controller.data || {};
    }

    get accountingStockValuation() {
        return this.formatMonetary(this.data.accounting_stock_valuation);
    }

    get inventoryValuation() {
        return formatMonetary(this.data.inventory_valuation.value, {
            currencyId: this.data.currency_id,
        });
    }

    get stockInitial() {
        return this.formatMonetary(this.data.stock_initial);
    }

    get stockVariation() {
        return this.formatMonetary(this.data.stock_variation);
    }

    // On Click Methods --------------------------------------------------------
    openAccountMoves(accountMoves=false) {
        const additionalContext = {};
        const domain = [];
        if (accountMoves) {
            const ids = accountMoves.map((am) => am.id);
            const names = accountMoves.map((am) => am.name);
            additionalContext.search_default_name = names;
            additionalContext.search_default_ids = ids;
            domain.push(["id", "in", ids])
        }
        return this.actionService.doAction(
            "account.action_move_journal_line",
            { additionalContext, domain }
        );
    }

    openInventoryLoss() {
        console.log("-- TODO");
    }

    openStockReport(line=false) {
        const additionalContext = {};
        const resModel = line?.res_model;
        if (resModel === "product.category") {
            additionalContext.search_default_categ_id = line.id;
        } else if (resModel === "product.product") {
            additionalContext.search_default_name = line.name;
        }
        return this.actionService.doAction(
            "stock.action_product_stock_view",
            { additionalContext }
        );
    }

    toggleInventoryValuationFold() {
        this.state.displayInventoryValuationLine = !this.state.displayInventoryValuationLine;
    }
}

registry.category("actions").add("stock_valuation_report", StockValuationReport);
