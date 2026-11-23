import { Component, onWillStart, proxy, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatDate, serializeDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { download } from "@web/core/network/download";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

const { DateTime } = luxon;

const COMPARE_MODES = [
    { id: "none", label: _t("No comparison") },
    { id: "previous", label: _t("Previous period") },
    { id: "last_year", label: _t("Same period last year") },
    { id: "custom", label: _t("Custom") },
];

export class FsReport extends Component {
    static template = "account_fs_report.FsReport";
    static components = { ControlPanel, Dropdown, DropdownItem, CheckboxItem };
    props = useProps(standardActionServiceProps);

    asOfRef = signal.ref();
    customDateRef = signal.ref();

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.compareModes = COMPARE_MODES;
        this.loadToken = 0;
        this.state = proxy({
            asOf: DateTime.now().startOf("day"),
            compare: "none",
            customDate: DateTime.now().minus({ months: 1 }).startOf("day"),
            targetMove: "posted",
            journalIds: [],
            journals: [],
            lines: [],
            accountLines: {},
            loading: true,
        });
        const component = this;
        this.asOfPicker = useDateTimePicker({
            target: this.asOfRef,
            get pickerProps() {
                return { value: component.state.asOf, type: "date" };
            },
            onApply: (date) => this.onAsOfApplied(date),
        });
        this.customDatePicker = useDateTimePicker({
            target: this.customDateRef,
            get pickerProps() {
                return { value: component.state.customDate, type: "date" };
            },
            onApply: (date) => this.onCustomDateApplied(date),
        });
        onWillStart(() => this.start());
    }

    get reportId() {
        return this.props.action.context.report_id;
    }

    get companyIds() {
        // Odoo 20: user.activeCompany is the current/main company (not companyService.currentCompany).
        const current = user.activeCompany;
        const ids = user.activeCompanies.map((company) => company.id);
        return [current.id, ...ids.filter((id) => id !== current.id)];
    }

    get selectedCompanies() {
        const ids = new Set(this.companyIds);
        const current = user.activeCompany;
        const rest = user.activeCompanies.filter((company) => company.id !== current.id && ids.has(company.id));
        return [current, ...rest].filter((company) => ids.has(company.id));
    }

    get companiesHeader() {
        if (this.selectedCompanies.length <= 1) {
            return "";
        }
        return this.selectedCompanies.map((company) => company.name).join(", ");
    }

    get balanceColumnLabel() {
        return _t("Balance");
    }

    get compareLabel() {
        return COMPARE_MODES.find((mode) => mode.id === this.state.compare).label;
    }

    get targetMoveLabel() {
        return this.state.targetMove === "posted" ? _t("Posted Entries") : _t("All Entries");
    }

    get journalLabel() {
        if (!this.state.journalIds.length) {
            return _t("Journals");
        }
        return _t("Journals (%s)", this.state.journalIds.length);
    }

    get options() {
        const columns = [];
        if (this.state.compare === "previous") {
            columns.push(this.column(this.state.asOf.minus({ months: 1 })));
        } else if (this.state.compare === "last_year") {
            columns.push(this.column(this.state.asOf.minus({ years: 1 })));
        } else if (this.state.compare === "custom") {
            columns.push(this.column(this.state.customDate));
        }
        columns.push(this.column(this.state.asOf));
        return {
            company_ids: this.companyIds,
            target_move: this.state.targetMove,
            journal_ids: this.state.journalIds,
            columns,
        };
    }

    get displayRows() {
        const rows = [];
        for (const line of this.state.lines) {
            if (this.isHidden(line)) {
                continue;
            }
            // Enterprise inserts an empty spacer row above every level-0 line.
            if (line.level === 0) {
                rows.push({ kind: "spacer", key: `spacer-${line.id}`, level: 0 });
            }
            rows.push({ ...line, kind: "line", key: `line-${line.id}` });
            for (const account of this.state.accountLines[line.id] || []) {
                rows.push({
                    ...account,
                    kind: "account",
                    level: line.level + 1,
                    key: `account-${line.id}-${account.id}`,
                });
            }
        }
        return rows;
    }

    column(date) {
        return { label: formatDate(date), date_to: serializeDate(date) };
    }

    isHidden(line) {
        return line.hide_if_zero && line.columns.every((value) => !value);
    }

    get parentIdsWithChildren() {
        const ids = new Set();
        for (const line of this.state.lines) {
            if (line.parent_id) {
                ids.add(line.parent_id);
            }
        }
        return ids;
    }

    getRowClasses(row) {
        if (row.kind === "spacer") {
            return "empty";
        }
        // Enterprise: line_level_N + "unfolded" (bold) when always_unfolded parents
        // have visible children, or when a foldable line is expanded.
        let classes = `line_level_${row.level}`;
        const hasReportChildren = row.kind === "line" && this.parentIdsWithChildren.has(row.id);
        const accountsOpen = row.kind === "line" && Boolean(this.state.accountLines[row.id]);
        if (hasReportChildren || accountsOpen) {
            classes += " unfolded";
        }
        return classes;
    }

    getAmountClasses(row, value) {
        // Enterprise AccountReportLineCell: auditable + muted for 0 + text-danger for negatives.
        let classes = "o_fs_report_amount numeric line_cell";
        if (row.kind === "line" && row.auditable) {
            classes += " auditable";
        } else if (row.kind === "account") {
            classes += " auditable";
        }
        const sign = Math.sign(value);
        if (Object.is(sign, -0) || sign === 0) {
            classes += " muted";
        } else if (sign < 0) {
            classes += " text-danger";
        }
        return classes;
    }

    async onLineAction(row, ev) {
        ev?.stopPropagation?.();
        ev?.preventDefault?.();
        if (!row.action_id) {
            return;
        }
        await this.action.doAction(row.action_id);
    }

    onAuditAmount(row, columnIndex, ev) {
        ev?.stopPropagation?.();
        ev?.preventDefault?.();
        if (row.kind === "account") {
            this.onOpenAccount(row);
            return;
        }
        if (!row.auditable) {
            return;
        }
        // Mirror Enterprise audit: open journal items contributing to this line as-of date.
        const column = this.options.columns[columnIndex];
        const domain = [["date", "<=", column.date_to]];
        if (this.state.targetMove === "posted") {
            domain.push(["parent_state", "=", "posted"]);
        } else {
            domain.push(["parent_state", "!=", "cancel"]);
        }
        if (this.state.journalIds.length) {
            domain.push(["journal_id", "in", this.state.journalIds]);
        }
        if (row.code === "CYE" || row.code === "PYE") {
            domain.push([
                "account_id.account_type",
                "in",
                [
                    "income",
                    "income_other",
                    "expense_direct_cost",
                    "expense",
                    "expense_depreciation",
                    "expense_other",
                    "equity_unaffected",
                    "equity_retained",
                ],
            ]);
        } else if (row.kind === "line" && row.unfoldable) {
            // account_type lines: prefer opening the unfolded accounts list action via first account open
            this.onToggleLine(row);
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: row.name,
            res_model: "account.move.line",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain,
            context: { search_default_group_by_account: 1 },
        });
    }

    formatAmount(value) {
        return formatMonetary(value, { currencyId: user.activeCompany.currency_id });
    }

    isJournalSelected(journalId) {
        return this.state.journalIds.includes(journalId);
    }

    async start() {
        this.state.journals = await this.orm.searchRead(
            "account.journal",
            [["company_id", "in", this.companyIds]],
            ["name"]
        );
        await this.reload();
    }

    async reload() {
        const token = ++this.loadToken;
        this.state.loading = true;
        this.state.accountLines = {};
        const lines = await this.orm.call("fs.report.engine", "get_report_data", [
            this.reportId,
            this.options,
        ]);
        if (token !== this.loadToken) {
            return;
        }
        this.state.lines = lines;
        this.state.loading = false;
    }

    openAsOfPicker() {
        this.asOfPicker.open();
    }

    openCustomPicker() {
        this.customDatePicker.open();
    }

    onAsOfApplied(date) {
        if (!date) {
            return;
        }
        this.state.asOf = date.startOf("day");
        this.reload();
    }

    onCustomDateApplied(date) {
        if (!date) {
            return;
        }
        this.state.customDate = date.startOf("day");
        this.reload();
    }

    onCompareSelected(mode) {
        this.state.compare = mode;
        this.reload();
    }

    onToggleTargetMove() {
        this.state.targetMove = this.state.targetMove === "posted" ? "all" : "posted";
        this.reload();
    }

    onToggleJournal(journalId) {
        if (this.isJournalSelected(journalId)) {
            this.state.journalIds = this.state.journalIds.filter((id) => id !== journalId);
        } else {
            this.state.journalIds = [...this.state.journalIds, journalId];
        }
        this.reload();
    }

    async onToggleLine(line) {
        if (!line.unfoldable) {
            return;
        }
        if (this.state.accountLines[line.id]) {
            delete this.state.accountLines[line.id];
            return;
        }
        const accounts = await this.orm.call("fs.report.engine", "get_account_lines", [
            line.id,
            this.options,
        ]);
        this.state.accountLines[line.id] = accounts;
    }

    onOpenAccount(account) {
        const domain = [
            ["account_id", "=", account.id],
            ["date", "<=", serializeDate(this.state.asOf)],
        ];
        if (this.state.targetMove === "posted") {
            domain.push(["parent_state", "=", "posted"]);
        } else {
            domain.push(["parent_state", "!=", "cancel"]);
        }
        if (this.state.journalIds.length) {
            domain.push(["journal_id", "in", this.state.journalIds]);
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: account.name,
            res_model: "account.move.line",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain,
        });
    }

    onExportPdf() {
        return download({
            url: "/account_fs_report/export/pdf",
            data: {
                report_id: this.reportId,
                options: JSON.stringify(this.options),
            },
        });
    }

    onExportXlsx() {
        return download({
            url: "/account_fs_report/export/xlsx",
            data: {
                report_id: this.reportId,
                options: JSON.stringify(this.options),
            },
        });
    }
}

registry.category("actions").add("account_fs_report.main", FsReport);
