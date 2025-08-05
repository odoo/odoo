import { reactive } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
const { DateTime } = luxon;


export class StockValuationReportController {
    constructor(action) {
        this.action = action;
        this.actionService = useService("action");
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.state = reactive({
            date: DateTime.now(),
        });
    }

    async load() {
        await this.loadReportData();
        this.currencyId = this.data.currency_id;
        this.companyId = this.data.company_id;
    }

    async loadReportData() {
        const kwargs = {
            date: this.state.date.toFormat("yyyy-MM-dd"),
        };
        const res = await this.orm.call(
            "stock_account.stock.valuation.report",
            "get_report_values",
            [],
            kwargs
        );
        this.data = res.data;
        // Prepare the "Initial Balance" lines.
        this.data.initial_balance.lines = [];
        this.data.initial_balance.accounts = [];
        for (let [code, data] of Object.entries(this.data.initial_balance.lines_by_code)) {
            this.data.initial_balance.lines.push({
                label: code,
                accounts: data.accounts,
                value: data.value,
            });
            this.data.initial_balance.accounts.push(...data.accounts);
        }
        // Prepare the "Ending Stock" lines.
        this.data.ending_stock.lines = [];
        this.data.ending_stock.accounts = [];
        for (let [code, data] of Object.entries(this.data.ending_stock.lines_by_code)) {
            this.data.ending_stock.lines.push({
                label: code,
                accounts: data.accounts,
                value: data.value,
            });
            this.data.ending_stock.accounts.push(...data.accounts);
        }
    }

    async setDate(date) {
        this.state.date = date;
        await this.loadReportData();
    }

    // Actions -----------------------------------------------------------------
    async actionGenerateEntry() {
        const args = [[this.companyId]];
        const action = await this.orm.call("res.company", "action_close_stock_valuation", args);
        if (action) {
            this.actionService.doAction(action);
        }
    }

    actionPrintReport(format="pdf") {
        if (format === "pdf") {
            return this.orm.call("stock_account.stock.valuation.report", "action_print_as_pdf");
        } else if (format === "xlsx") {
            return this.orm.call("stock_account.stock.valuation.report", "action_print_as_xlsx");
        }
    }
}
