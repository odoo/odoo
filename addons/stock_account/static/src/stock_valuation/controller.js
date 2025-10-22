import { reactive } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { serializeDate } from "@web/core/l10n/dates";
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
            date: serializeDate(this.state.date),
        };
        const res = await this.orm.call(
            "stock_account.stock.valuation.report",
            "get_report_values",
            [],
            kwargs
        );
        this.data = res.data;
        // Prepare the "Inventory Loss" lines.
        if (this.data.inventory_loss) {
            for (const line of this.data.inventory_loss.lines) {
                line.account = this.data.accounts_by_id[line.account_id];
            }
        }
        // Prepare "Stock Variation" lines.
        for (const line of this.data.stock_variation.lines) {
            line.account = this.data.accounts_by_id[line.account_id];
        }
        // Prepare the "Initial Balance" lines.
        this.data.initial_balance.lines = [];
        this.data.initial_balance.accounts = [];
        for (let [accountId, data] of Object.entries(this.data.initial_balance.lines_by_account_id)) {
            const account = this.data.accounts_by_id[accountId];
            this.data.initial_balance.lines.push({
                label: account.display_name,
                value: data.value,
                account_id: accountId,
            });
            this.data.initial_balance.accounts.push(...data.accounts);
        }
        // Prepare the "Ending Stock" lines.
        this.data.ending_stock.lines = [];
        this.data.ending_stock.accounts = [];
        for (let [accountId, data] of Object.entries(this.data.ending_stock.lines_by_account_id)) {
            const account = this.data.accounts_by_id[accountId];
            this.data.ending_stock.lines.push({
                label: account?.display_name,
                value: data.value,
                account_id: accountId,
            });
            this.data.ending_stock.accounts.push(...data.accounts);
        }
    }

    async setDate(date) {
        this.state.date = date;
        this.dateAsString = date.toFormat('y-LL-dd HH:mm:ss');
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
