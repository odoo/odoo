import { Component, onWillStart, proxy, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { serializeDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useSetupAction } from "@web/search/action_hook";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";
import { FsReportFilterDate } from "../fs_report/filter_date";
import { computePeriodRange } from "../fs_report/period_utils";
import { getRoundingUnitNames, roundForUnit, roundingUnitLabel } from "../fs_report/rounding";
import { formatDate } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export class FsGeneralLedger extends Component {
    static template = "account_fs_report.FsGeneralLedger";
    static components = { ControlPanel, Dropdown, DropdownItem, FsReportFilterDate };
    props = useProps(standardActionServiceProps);

    rootRef = signal.ref();

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.loadToken = 0;
        this.roundingUnitNames = getRoundingUnitNames("$");
        useSetupAction({
            rootRef: this.rootRef,
            getLocalState: () => ({
                keep_journal_groups_options: true,
                ...this.serializeFilterState(),
            }),
        });
        if (this.props?.state?.keep_journal_groups_options !== undefined) {
            this.props.action.keep_journal_groups_options = true;
        }

        const today = DateTime.utc().startOf("day");
        this.state = proxy({
            loading: true,
            lines: [],
            currencyId: user.activeCompany.currency_id,
            hasUnposted: false,
            filterAccounts: "",
            accountIds: [],
            dateFrom: today.startOf("year"),
            dateTo: today,
            periodType: "year",
            fiscalStartDay: 1,
            fiscalStartMonth: 1,
            targetMove: "posted",
            journalIds: [],
            unfoldedAccountIds: [],
            searchInput: "",
            roundingUnit: "decimals",
        });

        onWillStart(() => this.start());
    }

    get companyIds() {
        const current = user.activeCompany;
        const ids = user.activeCompanies.map((company) => company.id);
        return [current.id, ...ids.filter((id) => id !== current.id)];
    }

    sessionOptionsID() {
        const mainId = user.activeCompany.id;
        const otherIds = user.activeCompanies
            .filter((company) => company.id !== mainId)
            .map((company) => company.id)
            .sort((a, b) => a - b);
        return `account_fs_report:general_ledger:${[mainId, ...otherIds].join(",")}`;
    }

    serializeFilterState() {
        return {
            date_from: serializeDate(this.state.dateFrom),
            date_to: serializeDate(this.state.dateTo),
            period_type: this.state.periodType,
            target_move: this.state.targetMove,
            journal_ids: this.state.journalIds || [],
            filter_accounts: this.state.filterAccounts,
            account_ids: this.state.accountIds || [],
            unfolded_account_ids: this.state.unfoldedAccountIds || [],
            rounding_unit: this.state.roundingUnit,
            search_input: this.state.searchInput,
        };
    }

    parseOptionDate(value) {
        if (!value) {
            return null;
        }
        return DateTime.fromISO(value, { zone: "utc" }).startOf("day");
    }

    applyFilterState(saved) {
        if (!saved) {
            return;
        }
        if (saved.date_from) {
            this.state.dateFrom = this.parseOptionDate(saved.date_from);
        }
        if (saved.date_to) {
            this.state.dateTo = this.parseOptionDate(saved.date_to);
        }
        // Accept snake_case (action params / session) and camelCase (localState).
        const periodType = saved.period_type || saved.periodType;
        if (periodType) {
            this.state.periodType = periodType;
        }
        if (saved.target_move) {
            this.state.targetMove = saved.target_move;
        }
        if (Array.isArray(saved.journal_ids)) {
            this.state.journalIds = saved.journal_ids;
        }
        if (saved.filter_accounts !== undefined) {
            this.state.filterAccounts = saved.filter_accounts || "";
            this.state.searchInput = saved.search_input ?? this.state.filterAccounts;
        }
        if (Array.isArray(saved.account_ids)) {
            this.state.accountIds = saved.account_ids;
        }
        if (Array.isArray(saved.unfolded_account_ids)) {
            this.state.unfoldedAccountIds = saved.unfolded_account_ids;
        }
        if (saved.rounding_unit) {
            this.state.roundingUnit = saved.rounding_unit;
        }
    }

    loadIncomingFilterState() {
        const local = this.props.state;
        if (local?.date_to || local?.period_type || local?.periodType) {
            return local;
        }
        const params = this.props.action.params || {};
        const ignoreSession = Boolean(params.ignore_session);
        if (!ignoreSession) {
            try {
                const raw = window.sessionStorage.getItem(this.sessionOptionsID());
                if (raw) {
                    return JSON.parse(raw);
                }
            } catch {
                // ignore
            }
        }
        return params.options || null;
    }

    saveSessionOptions() {
        window.sessionStorage.setItem(
            this.sessionOptionsID(),
            JSON.stringify(this.serializeFilterState())
        );
    }

    get options() {
        return {
            company_ids: this.companyIds,
            date_from: serializeDate(this.state.dateFrom),
            date_to: serializeDate(this.state.dateTo),
            target_move: this.state.targetMove,
            journal_ids: this.state.journalIds,
            filter_accounts: this.state.filterAccounts,
            account_ids: this.state.accountIds,
            unfolded_account_ids: this.state.unfoldedAccountIds,
        };
    }

    get targetMoveLabel() {
        return this.state.targetMove === "posted" ? _t("Posted Entries") : _t("With Draft Entries");
    }

    get roundingUnits() {
        return Object.keys(this.roundingUnitNames);
    }

    get roundingLabel() {
        return roundingUnitLabel(this.state.roundingUnit, this.roundingUnitNames);
    }

    roundingUnitName(unit) {
        return roundingUnitLabel(unit, this.roundingUnitNames);
    }

    get displayRows() {
        const rows = [];
        for (const line of this.state.lines) {
            rows.push(line);
            if (line.unfolded) {
                for (const child of line.children || []) {
                    rows.push(child);
                }
            }
        }
        return rows;
    }

    formatDateValue(value) {
        return formatDate(value);
    }

    formatAmount(value) {
        const scaled = roundForUnit(value, this.state.roundingUnit);
        return formatMonetary(scaled, {
            currencyId: this.state.currencyId,
            digits: this.state.roundingUnit === "decimals" ? undefined : [0, 0],
        });
    }

    formatAmountCurrency(row) {
        if (row.amount_currency === false || row.amount_currency === undefined) {
            return "";
        }
        return formatMonetary(row.amount_currency, {
            currencyId: row.currency_id || this.state.currencyId,
        });
    }

    formatRowDate(row) {
        if (!row.date) {
            return "";
        }
        return formatDate(DateTime.fromISO(row.date));
    }

    amountClass(value) {
        const sign = Math.sign(value);
        if (Object.is(sign, -0) || sign === 0) {
            return "muted";
        }
        if (sign < 0) {
            return "text-danger";
        }
        return "";
    }

    async start() {
        const companies = await this.orm.read(
            "res.company",
            [user.activeCompany.id],
            ["currency_id", "fiscalyear_last_day", "fiscalyear_last_month"]
        );
        const company = companies[0];
        if (company?.currency_id) {
            const currencies = await this.orm.read(
                "res.currency",
                [company.currency_id[0]],
                ["symbol"]
            );
            if (currencies[0]?.symbol) {
                this.roundingUnitNames = getRoundingUnitNames(currencies[0].symbol);
            }
        }
        if (company) {
            const lastMonth = parseInt(company.fiscalyear_last_month, 10) || 12;
            const lastDay = company.fiscalyear_last_day || 31;
            const defaultYear = lastMonth === 2 && lastDay === 29 ? 2024 : 2025;
            const fyEnd = DateTime.utc(defaultYear, lastMonth, lastDay);
            const fyStart = fyEnd.plus({ days: 1 });
            this.state.fiscalStartDay = fyStart.day;
            this.state.fiscalStartMonth = fyStart.month;
        }
        // Enterprise GL default: this fiscal year (range).
        const today = DateTime.utc().startOf("day");
        const [dateFrom, dateTo] = computePeriodRange(
            today,
            this.state.fiscalStartDay,
            this.state.fiscalStartMonth,
            12
        );
        this.state.periodType = "year";
        this.state.dateFrom = dateFrom;
        this.state.dateTo = dateTo;

        const ctx = this.props.action.context || {};
        if (ctx.default_filter_accounts && !this.props.state?.filter_accounts) {
            this.state.filterAccounts = ctx.default_filter_accounts;
            this.state.searchInput = ctx.default_filter_accounts;
        }
        this.applyFilterState(this.loadIncomingFilterState());
        delete this.props.action.params?.ignore_session;
        await this.reload();
    }

    onDatePeriodSelected({ periodType, dateFrom, dateTo }) {
        this.state.periodType = periodType;
        this.state.dateFrom = dateFrom ? dateFrom.startOf("day") : this.state.dateFrom;
        this.state.dateTo = dateTo.startOf("day");
        this.reload();
    }

    async reload() {
        const token = ++this.loadToken;
        this.state.loading = true;
        this.saveSessionOptions();
        const data = await this.orm.call("fs.general.ledger", "get_report_data", [this.options]);
        if (token !== this.loadToken) {
            return;
        }
        this.state.lines = data.lines;
        this.state.currencyId = data.currency_id;
        this.state.hasUnposted = data.has_unposted;
        this.state.loading = false;
        this.saveSessionOptions();
    }

    onSearchSubmit(ev) {
        ev.preventDefault();
        this.state.filterAccounts = this.state.searchInput.trim();
        this.state.accountIds = [];
        this.reload();
    }

    onSetTargetMove(value) {
        this.state.targetMove = value;
        this.reload();
    }

    onSetRoundingUnit(unit) {
        this.state.roundingUnit = unit;
        this.saveSessionOptions();
    }

    async onOpenUnpostedMoves() {
        const action = await this.orm.call("fs.general.ledger", "open_unposted_moves", [
            this.options,
        ]);
        return this.action.doAction(action);
    }

    async onToggleAccount(line) {
        if (!line.unfoldable) {
            return;
        }
        const id = line.account_id;
        if (this.state.unfoldedAccountIds.includes(id)) {
            this.state.unfoldedAccountIds = this.state.unfoldedAccountIds.filter((item) => item !== id);
        } else {
            this.state.unfoldedAccountIds = [...this.state.unfoldedAccountIds, id];
        }
        await this.reload();
    }

    async onOpenJournalItems(line, ev) {
        ev.stopPropagation();
        const action = await this.orm.call("fs.general.ledger", "open_journal_items", [
            this.options,
            { account_id: line.account_id },
        ]);
        return this.action.doAction(action);
    }

    onOpenMove(row) {
        if (!row.move_id) {
            return;
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: row.move_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    onPrint() {
        window.print();
    }
}

registry.category("actions").add("account_fs_report.general_ledger", FsGeneralLedger);
