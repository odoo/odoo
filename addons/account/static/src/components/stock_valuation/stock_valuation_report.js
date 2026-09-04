import { useSubEnv } from "@web/owl2/utils";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { serializeDate } from "@web/core/l10n/dates";
const { DateTime } = luxon;

import { Component, onWillStart, proxy } from "@odoo/owl";

import { StockValuationReportButtonsBar } from "./buttons_bar/buttons_bar"
import { StockValuationReportController } from "./controller"
import { StockValuationReportFilters } from "./filters/filters"
import { StockValuationReportLine } from "./line/line"


export class StockValuationReport extends Component {
    static template = "account.StockValuationReport";
    static props = { ...standardActionServiceProps };
    static components = {
        ControlPanel,
        StockValuationReportButtonsBar,
        StockValuationReportFilters,
        StockValuationReportLine,
    };

    setup() {
        this.controller = proxy(new StockValuationReportController(this.props.action));
        this.state = proxy({
            displayInventoryValuationLine: false,
        })
        this.orm = useService("orm");
        this.actionService = useService("action");

        onWillStart(async () => {
            await this.controller.load(this.data);
        })

        useSubEnv({
            controller: this.controller,
            formatMonetary: this.formatMonetary.bind(this),
        });
    }

    formatMonetary(value) {
        return formatMonetary(value, {
            currencyId: this.data.currency_id,
        });
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
    async openAccountMoves(accountIds=false) {
        const action = await this.actionService.loadAction("account.action_account_moves_all");
        const domain = [...(action.domain || [])];
        if (accountIds) {
            domain.push(['account_id', 'in', accountIds]);
        }
        if (serializeDate(this.controller.state.date) !== serializeDate(DateTime.now())) {
            domain.push(['date', '<=', serializeDate(this.controller.state.date)]);
        }
        action.domain = domain;
        action.context = {
            ...action.context,
            search_default_group_by_account: 1,
            search_default_groupby_date: 'month',
        };
        return this.actionService.doAction(action);
    }

    openStockReport() {
        return this.actionService.doAction({
            name: _t("Products"),
            type: "ir.actions.act_window",
            res_model: "product.product",
            domain: [["is_storable", "=", true]],
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    toggleInventoryValuationFold() {
        this.state.displayInventoryValuationLine = !this.state.displayInventoryValuationLine;
    }
}

registry.category("actions").add("stock_valuation_report", StockValuationReport);
