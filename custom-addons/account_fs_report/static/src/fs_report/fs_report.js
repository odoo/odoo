import { Component, onWillStart, proxy, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatDate, serializeDate } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { usePopover } from "@web/core/popover/popover_hook";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useSetupAction } from "@web/search/action_hook";
import { download } from "@web/core/network/download";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";
import { FsReportDebugPopover } from "./debug_popover";
import { FsReportFilterComparison } from "./filter_comparison";
import { FsReportFilterDate } from "./filter_date";
import { FsReportFilterExtraOptions } from "./filter_extra_options";
import {
    buildRangeDateLabel,
    computePeriodRange,
    shiftPreviousPeriodDate,
    shiftPreviousPeriodRange,
    shiftSameLastYearDate,
    shiftSameLastYearRange,
} from "./period_utils";
import { formatReportAmount, getRoundingUnitNames, roundingUnitLabel } from "./rounding";

const { DateTime } = luxon;

export class FsReport extends Component {
    static template = "account_fs_report.FsReport";
    static components = {
        ControlPanel,
        Dropdown,
        DropdownItem,
        FsReportFilterDate,
        FsReportFilterComparison,
        FsReportFilterExtraOptions,
    };
    props = useProps(standardActionServiceProps);

    rootRef = signal.ref();

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.ui = useService("ui");
        // Enterprise: export filters on leave so breadcrumb restore keeps Fiscal Year etc.
        useSetupAction({
            rootRef: this.rootRef,
            // Enterprise: keep_journal_groups_options marks breadcrumb restore; also export filters.
            getLocalState: () => ({
                keep_journal_groups_options: true,
                ...this.serializeFilterState(),
            }),
        });
        if (this.props?.state?.keep_journal_groups_options !== undefined) {
            this.props.action.keep_journal_groups_options = true;
        }
        this.debugPopover = usePopover(FsReportDebugPopover, {
            closeOnClickAway: true,
            position: localization.direction === "rtl" ? "left" : "right",
        });
        this.loadToken = 0;
        this.roundingUnitNames = getRoundingUnitNames("$", "USD");
        this.currencyDecimalPlaces = 2;
        this.reportType = "balance_sheet";
        this.state = proxy({
            // Enterprise account_reports filters use DateTime.utc() for as-of dates.
            asOf: DateTime.utc().startOf("day"),
            dateFrom: false,
            periodType: "today",
            fiscalStartDay: 1,
            fiscalStartMonth: 1,
            compare: "no_comparison",
            numberPeriod: 1,
            periodOrder: "descending",
            growthDisplay: "percent",
            // Enterprise Specific Date defaults to the current as-of date.
            customDate: DateTime.utc().startOf("day"),
            customDateFrom: false,
            baseReportLineId: false,
            targetMove: "posted",
            journalIds: [],
            roundingUnit: "decimals",
            unfoldAll: false,
            hide0Lines: false,
            horizontalSplit: false,
            lines: [],
            accountLines: {},
            loading: true,
            hasUnposted: false,
        });
        onWillStart(() => this.start());
    }

    get reportId() {
        return this.props.action.context.report_id;
    }

    /** Enterprise filter_date.range_mode — true for P&L / Cash Flow. */
    get isRangeMode() {
        return this.reportType === "period" || this.reportType === "cash_flow";
    }

    /** Enterprise Direct CF: filter_period_comparison=False. */
    get showComparisonFilter() {
        return this.reportType !== "cash_flow";
    }

    get showHorizontalSplit() {
        return !this.isRangeMode;
    }

    /**
     * Enterprise controller.sessionOptionsID — persist filters per report + companies
     * so breadcrumb / menu reopen keeps Fiscal Year (etc.) after GL / Journal Items.
     */
    sessionOptionsID() {
        const mainId = user.activeCompany.id;
        const otherIds = user.activeCompanies
            .filter((company) => company.id !== mainId)
            .map((company) => company.id)
            .sort((a, b) => a - b);
        return `account_fs_report:${this.reportId}:${[mainId, ...otherIds].join(",")}`;
    }

    hasSessionOptions() {
        return Boolean(window.sessionStorage.getItem(this.sessionOptionsID()));
    }

    saveSessionOptions() {
        window.sessionStorage.setItem(
            this.sessionOptionsID(),
            JSON.stringify(this.serializeFilterState())
        );
    }

    sessionOptions() {
        try {
            return JSON.parse(window.sessionStorage.getItem(this.sessionOptionsID()));
        } catch {
            return null;
        }
    }

    serializeFilterState() {
        return {
            periodType: this.state.periodType,
            date_from: this.state.dateFrom ? serializeDate(this.state.dateFrom) : false,
            date_to: serializeDate(this.state.asOf),
            compare: this.state.compare,
            numberPeriod: this.state.numberPeriod,
            periodOrder: this.state.periodOrder,
            growthDisplay: this.state.growthDisplay,
            customDate: this.state.customDate ? serializeDate(this.state.customDate) : false,
            customDateFrom: this.state.customDateFrom
                ? serializeDate(this.state.customDateFrom)
                : false,
            baseReportLineId: this.state.baseReportLineId || false,
            targetMove: this.state.targetMove,
            journalIds: this.state.journalIds || [],
            roundingUnit: this.state.roundingUnit,
            unfoldAll: this.state.unfoldAll,
            hide0Lines: this.state.hide0Lines,
            horizontalSplit: this.state.horizontalSplit,
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
        const periodType = saved.periodType || saved.period_type;
        if (periodType) {
            this.state.periodType = periodType;
        }
        if (saved.date_to) {
            this.state.asOf = this.parseOptionDate(saved.date_to);
        }
        if (saved.date_from) {
            this.state.dateFrom = this.parseOptionDate(saved.date_from);
        } else if (saved.date_from === false) {
            this.state.dateFrom = false;
        }
        if (saved.compare) {
            this.state.compare = saved.compare;
        }
        if (saved.numberPeriod >= 1) {
            this.state.numberPeriod = saved.numberPeriod;
        }
        if (saved.periodOrder) {
            this.state.periodOrder = saved.periodOrder;
        }
        if (saved.growthDisplay) {
            this.state.growthDisplay = saved.growthDisplay;
        }
        if (saved.customDate) {
            this.state.customDate = this.parseOptionDate(saved.customDate);
        }
        if (saved.customDateFrom) {
            this.state.customDateFrom = this.parseOptionDate(saved.customDateFrom);
        } else if (saved.customDateFrom === false) {
            this.state.customDateFrom = false;
        }
        if (saved.baseReportLineId !== undefined) {
            this.state.baseReportLineId = saved.baseReportLineId;
        }
        if (saved.targetMove) {
            this.state.targetMove = saved.targetMove;
        }
        if (Array.isArray(saved.journalIds)) {
            this.state.journalIds = saved.journalIds;
        }
        if (saved.roundingUnit) {
            this.state.roundingUnit = saved.roundingUnit;
        }
        if (typeof saved.unfoldAll === "boolean") {
            this.state.unfoldAll = saved.unfoldAll;
        }
        if (typeof saved.hide0Lines === "boolean") {
            this.state.hide0Lines = saved.hide0Lines;
        }
        if (typeof saved.horizontalSplit === "boolean") {
            this.state.horizontalSplit = saved.horizontalSplit;
        }
    }

    /**
     * Restore priority (Enterprise controller.loadReportOptions):
     * 1) action.params.options when ignore_session (CYE → P&L / linked report)
     * 2) props.state from getLocalState (breadcrumb)
     * 3) sessionStorage (menu reopen)
     */
    loadIncomingFilterState() {
        const params = this.props.action.params || {};
        const ignoreSession = Boolean(params.ignore_session);
        // Enterprise: ignore_session always wins over session (and over stale local state).
        if (ignoreSession && params.options) {
            return params.options;
        }
        const local = this.props.state;
        if (local?.date_to || local?.periodType || local?.period_type) {
            return local;
        }
        if (!ignoreSession && this.hasSessionOptions()) {
            return this.sessionOptions();
        }
        return params.options || null;
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

    get hasDebugColumn() {
        return this.state.lines.some((line) => line.debug_popup_data);
    }

    hasDebugData(row) {
        return Boolean(row.kind === "line" && row.debug_popup_data);
    }

    showDebugPopover(ev, row) {
        if (!row.debug_popup_data) {
            return;
        }
        const close = () => this.debugPopover.close();
        this.debugPopover.open(ev.currentTarget, {
            expressionsDetail: JSON.parse(row.debug_popup_data).expressions_detail,
            close,
            onClose: close,
        });
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

    /** Enterprise: one or two tables when horizontal_split is on (BS only). */
    get splitSides() {
        return this.state.horizontalSplit && this.showHorizontalSplit ? ["left", "right"] : ["left"];
    }

    /**
     * Build comparison period dates (Enterprise comparison.periods), oldest-of-loop first
     * being the most recent previous period at index 0.
     */
    get comparisonPeriods() {
        const periods = [];
        if (this.state.compare === "custom") {
            if (this.isRangeMode) {
                periods.push(this.column(
                    this.state.customDateFrom || this.state.dateFrom,
                    this.state.customDate,
                    "custom"
                ));
            } else {
                periods.push(this.column(false, this.state.customDate, "custom"));
            }
            return periods;
        }
        if (
            this.state.compare !== "previous_period" &&
            this.state.compare !== "same_last_year"
        ) {
            return periods;
        }
        if (this.isRangeMode) {
            let dateFrom = this.state.dateFrom;
            let dateTo = this.state.asOf;
            for (let index = 0; index < this.state.numberPeriod; index++) {
                if (this.state.compare === "previous_period") {
                    [dateFrom, dateTo] = shiftPreviousPeriodRange(
                        dateFrom,
                        dateTo,
                        this.state.periodType,
                        this.state.fiscalStartDay,
                        this.state.fiscalStartMonth
                    );
                } else {
                    [dateFrom, dateTo] = shiftSameLastYearRange(dateFrom, dateTo);
                }
                periods.push(this.column(dateFrom, dateTo));
            }
            return periods;
        }
        let cursor = this.state.asOf;
        for (let index = 0; index < this.state.numberPeriod; index++) {
            if (this.state.compare === "previous_period") {
                cursor = shiftPreviousPeriodDate(
                    cursor,
                    this.state.periodType,
                    this.state.fiscalStartDay,
                    this.state.fiscalStartMonth
                );
            } else {
                cursor = shiftSameLastYearDate(cursor);
            }
            periods.push(this.column(false, cursor));
        }
        return periods;
    }

    get currentPeriodColumn() {
        if (this.isRangeMode) {
            return this.column(this.state.dateFrom, this.state.asOf);
        }
        return this.column(false, this.state.asOf);
    }

    get dateString() {
        if (this.isRangeMode) {
            return buildRangeDateLabel(
                this.state.dateFrom,
                this.state.asOf,
                this.state.periodType,
                this.state.fiscalStartDay,
                this.state.fiscalStartMonth
            );
        }
        return _t("As of %s", formatDate(this.state.asOf));
    }

    get options() {
        // Enterprise descending: [current, ...previous periods]
        let columns = [this.currentPeriodColumn, ...this.comparisonPeriods];
        if (this.state.periodOrder === "ascending") {
            columns = columns.slice().reverse();
        }
        const date = {
            string: this.dateString,
            date_to: serializeDate(this.state.asOf),
            period_type: this.state.periodType,
        };
        if (this.isRangeMode && this.state.dateFrom) {
            date.date_from = serializeDate(this.state.dateFrom);
        }
        return {
            company_ids: this.companyIds,
            companies: this.selectedCompanies.map((company) => ({
                id: company.id,
                name: company.name,
            })),
            date,
            target_move: this.state.targetMove,
            journal_ids: this.state.journalIds,
            columns,
            comparison: {
                filter: this.state.compare,
                number_period: this.state.numberPeriod,
                period_order: this.state.periodOrder,
                base_report_line_id: this.state.baseReportLineId || false,
            },
            growth_display: this.state.growthDisplay,
            unfold_all: this.state.unfoldAll,
            report_type: this.reportType,
            report_id: this.reportId,
        };
    }

    /** Growth / % column when Enterprise would show column_percent_comparison. */
    get showGrowthColumn() {
        if (this.state.compare === "report_line" && this.state.baseReportLineId) {
            return true;
        }
        return (
            this.comparisonPeriods.length === 1 &&
            ["previous_period", "same_last_year", "custom"].includes(this.state.compare)
        );
    }

    get growthColumnLabel() {
        if (this.state.compare === "report_line") {
            return _t("Change (%)");
        }
        if (this.state.growthDisplay === "amount") {
            return _t("Change (%s)", this.roundingUnitNames.units || "$");
        }
        return _t("Change (%)");
    }

    get tableColspan() {
        return (
            1 +
            this.options.columns.length +
            (this.showGrowthColumn ? 1 : 0) +
            (this.hasDebugColumn ? 1 : 0)
        );
    }

    get baseReportLineValue() {
        if (!this.state.baseReportLineId) {
            return null;
        }
        const baseId = Number(this.state.baseReportLineId);
        const line = this.state.lines.find((row) => Number(row.id) === baseId);
        if (!line || !line.columns?.length) {
            return null;
        }
        return line.columns[0];
    }

    /**
     * Build visible report rows for one split side (or the full report).
     * Mirrors Enterprise setLineVisibility + hideZeroLines when hide_0_lines is on.
     */
    displayRowsForSide(splitSide = "left") {
        const rows = [];
        for (const line of this.state.lines) {
            if (this.state.horizontalSplit) {
                const side = line.horizontal_split_side || "left";
                if (side !== splitSide) {
                    continue;
                }
            }
            if (this.isHidden(line)) {
                continue;
            }
            // Enterprise inserts an empty spacer row above every level-0 line.
            if (line.level === 0) {
                rows.push({
                    kind: "spacer",
                    key: `spacer-${splitSide}-${line.id}`,
                    level: 0,
                    parent_id: false,
                    columns: [],
                });
            }
            rows.push({ ...line, kind: "line", key: `line-${splitSide}-${line.id}` });
            for (const account of this.state.accountLines[line.id] || []) {
                rows.push({
                    ...account,
                    kind: "account",
                    level: line.level + 1,
                    parent_id: line.id,
                    green_on_positive: line.green_on_positive,
                    horizontal_split_side: line.horizontal_split_side,
                    key: `account-${splitSide}-${line.id}-${account.id}`,
                });
            }
        }
        if (this.state.hide0Lines) {
            this.applyHideZeroLines(rows);
            return rows.filter((row) => row.kind === "spacer" ? this._spacerVisible(row, rows) : row.visible !== false);
        }
        return rows;
    }

    _spacerVisible(spacer, rows) {
        const index = rows.indexOf(spacer);
        for (let i = index + 1; i < rows.length; i++) {
            const row = rows[i];
            if (row.kind === "spacer") {
                break;
            }
            if (row.visible !== false) {
                return true;
            }
        }
        return false;
    }

    /** Enterprise AccountReportController.hideZeroLines — reverse walk. */
    applyHideZeroLines(rows) {
        const hasVisibleChildren = new Set();
        for (let i = rows.length - 1; i >= 0; i--) {
            const row = rows[i];
            if (row.kind === "spacer") {
                continue;
            }
            const columns = row.columns || [];
            // Empty columns → treat as zero (Enterprise: all numeric cells is_zero).
            const isZero =
                columns.length === 0 ||
                columns.every((value) => Math.abs(Number(value) || 0) < 0.005);
            if (!hasVisibleChildren.has(row.id) && isZero) {
                row.visible = false;
            } else {
                row.visible = true;
            }
            if (row.parent_id && row.visible) {
                hasVisibleChildren.add(row.parent_id);
            }
        }
    }

    column(dateFrom, dateTo, periodType = null) {
        const type = periodType || this.state.periodType;
        if (this.isRangeMode && dateFrom) {
            return {
                label: buildRangeDateLabel(
                    dateFrom,
                    dateTo,
                    type,
                    this.state.fiscalStartDay,
                    this.state.fiscalStartMonth
                ),
                date_from: serializeDate(dateFrom),
                date_to: serializeDate(dateTo),
            };
        }
        // Enterprise _build_date_label (single mode): "As of <date>"
        return {
            label: _t("As of %s", formatDate(dateTo)),
            date_to: serializeDate(dateTo),
        };
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
        if (row.css_class) {
            classes += ` ${row.css_class}`;
        }
        return classes;
    }

    getAmountClasses(row, value, cellIndex = 0) {
        // Enterprise AccountReportLineCell: auditable + muted for 0 + text-danger for negatives.
        // Odd balance columns get line_cell_odd (striped comparison column).
        let classes = "o_fs_report_amount numeric line_cell";
        if (row.kind === "line" && row.auditable) {
            classes += " auditable";
        } else if (row.kind === "account") {
            classes += " auditable";
        }
        if (cellIndex % 2) {
            classes += " line_cell_odd";
        }
        const sign = Math.sign(value);
        if (Object.is(sign, -0) || sign === 0) {
            classes += " muted";
        } else if (sign < 0) {
            classes += " text-danger";
        }
        return classes;
    }

    getTableClasses() {
        // Enterprise: striped when more than one balance column; w-50 when split.
        let classes = "table table-sm table-hover table-borderless o_fs_report_table mx-auto";
        if (this.options.columns.length > 1) {
            classes += " striped";
        }
        if (this.state.horizontalSplit) {
            classes += " w-50 mx-2";
        }
        return classes;
    }

    async onLineAction(row, ev) {
        ev?.stopPropagation?.();
        ev?.preventDefault?.();
        if (!row.action_id) {
            return;
        }
        // Enterprise line_name.triggerAction → account.report.execute_action
        const action = await this.orm.call("fs.report.engine", "execute_action", [
            this.options,
            { id: row.id, actionId: row.action_id },
        ]);
        return this.action.doAction(action);
    }

    async onAuditAmount(row, columnIndex, ev) {
        ev?.stopPropagation?.();
        ev?.preventDefault?.();
        // Enterprise: figure click → action_audit_cell → Journal Items (caret opens GL).
        if (row.kind === "account") {
            const action = await this.orm.call("fs.report.engine", "action_audit_cell", [
                this.options,
                { account_id: row.id, column_index: columnIndex },
            ]);
            return this.action.doAction(action);
        }
        if (!row.auditable) {
            return;
        }
        const action = await this.orm.call("fs.report.engine", "action_audit_cell", [
            this.options,
            { line_id: row.id, column_index: columnIndex },
        ]);
        return this.action.doAction(action);
    }

    formatAmount(value) {
        // Enterprise BS (single currency): formatLang without currency_obj + rounding_unit.
        return formatReportAmount(
            value,
            this.state.roundingUnit,
            this.currencyDecimalPlaces
        );
    }

    async start() {
        const [reports, companies] = await Promise.all([
            this.orm.read("fs.report", [this.reportId], ["name", "code", "report_type"]),
            this.orm.read(
                "res.company",
                [user.activeCompany.id],
                ["currency_id", "fiscalyear_last_day", "fiscalyear_last_month"]
            ),
        ]);
        const report = reports[0];
        if (report?.report_type) {
            this.reportType = report.report_type;
        }
        const company = companies[0];
        if (company?.currency_id) {
            const currencies = await this.orm.read(
                "res.currency",
                [company.currency_id[0]],
                ["symbol", "name", "decimal_places"]
            );
            const currency = currencies[0];
            if (currency?.symbol) {
                this.roundingUnitNames = getRoundingUnitNames(currency.symbol, currency.name);
            }
            if (typeof currency?.decimal_places === "number") {
                this.currencyDecimalPlaces = currency.decimal_places;
            }
        }
        if (company) {
            // Mirror Enterprise: fiscal period start = day after fiscalyear last day/month.
            const lastMonth = parseInt(company.fiscalyear_last_month, 10) || 12;
            const lastDay = company.fiscalyear_last_day || 31;
            const defaultYear = lastMonth === 2 && lastDay === 29 ? 2024 : 2025;
            const fyEnd = DateTime.utc(defaultYear, lastMonth, lastDay);
            const fyStart = fyEnd.plus({ days: 1 });
            this.state.fiscalStartDay = fyStart.day;
            this.state.fiscalStartMonth = fyStart.month;
        }
        // Enterprise P&L default_opening_date_filter = this_year.
        if (this.isRangeMode) {
            const today = DateTime.utc().startOf("day");
            const [dateFrom, dateTo] = computePeriodRange(
                today,
                this.state.fiscalStartDay,
                this.state.fiscalStartMonth,
                12
            );
            this.state.periodType = "year";
            this.state.dateFrom = dateFrom;
            this.state.asOf = dateTo;
            this.state.customDate = dateTo;
            this.state.customDateFrom = dateFrom;
        }
        // Enterprise: restore session (or action.params.options) after defaults so
        // breadcrumb / reopen keeps Fiscal Year 2025 after visiting GL / journal.
        this.applyFilterState(this.loadIncomingFilterState());
        delete this.props.action.params?.ignore_session;
        await this.reload();
    }

    onDatePeriodSelected({ periodType, dateFrom, dateTo }) {
        this.state.periodType = periodType;
        this.state.asOf = dateTo.startOf("day");
        this.state.dateFrom = dateFrom ? dateFrom.startOf("day") : false;
        // Keep custom comparison defaults aligned with the active period (Enterprise).
        if (this.state.compare !== "custom") {
            this.state.customDate = this.state.asOf;
            this.state.customDateFrom = this.state.dateFrom;
        }
        this.reload();
    }

    onComparisonChange(patch) {
        Object.assign(this.state, patch);
        this.reload();
    }

    onSetRoundingUnit(unit) {
        this.state.roundingUnit = unit;
        this.saveSessionOptions();
    }

    /** Enterprise all_entries toggle → Draft Entries. */
    onToggleDraftEntries() {
        this.state.targetMove = this.state.targetMove === "posted" ? "all" : "posted";
        this.reload();
    }

    /** Enterprise unfold_all — expand/collapse every unfoldable account-type line. */
    async onToggleUnfoldAll() {
        const next = !this.state.unfoldAll;
        this.state.unfoldAll = next;
        if (!next) {
            this.state.accountLines = {};
            return;
        }
        await this.unfoldAllLines();
    }

    async unfoldAllLines() {
        const unfoldable = this.state.lines.filter((line) => line.unfoldable);
        const accountLines = {};
        await Promise.all(
            unfoldable.map(async (line) => {
                accountLines[line.id] = await this.orm.call("fs.report.engine", "get_account_lines", [
                    line.id,
                    this.options,
                ]);
            })
        );
        this.state.accountLines = accountLines;
    }

    /** Enterprise hide_0_lines — client-side visibility only (no reload). BS + P&L. */
    onToggleHide0Lines() {
        this.state.hide0Lines = !this.state.hide0Lines;
        // Drop cached account expansions' visibility by rebuilding rows on next render.
        this.state.accountLines = { ...this.state.accountLines };
        this.saveSessionOptions();
    }

    /** Enterprise horizontal_split — Assets left / Liabilities+Equity right. */
    onToggleHorizontalSplit() {
        this.state.horizontalSplit = !this.state.horizontalSplit;
        this.saveSessionOptions();
    }

    async reload() {
        const token = ++this.loadToken;
        this.state.loading = true;
        this.state.accountLines = {};
        // Persist filters before RPC so breadcrumb back from GL/journal keeps them
        // even if the user navigates away while loading (Enterprise session parity).
        this.saveSessionOptions();
        // report_line % mode still needs balances for the current as-of column only.
        const data = await this.orm.call("fs.report.engine", "get_report_data", [
            this.reportId,
            this.options,
        ]);
        if (token !== this.loadToken) {
            return;
        }
        this.state.lines = data.lines;
        this.state.hasUnposted = Boolean(data.has_unposted);
        // Cash Flow (and any line with embedded accounts + default_unfolded):
        // seed account expansions without a second RPC (Enterprise always returns AMLs).
        const seeded = {};
        for (const line of data.lines || []) {
            if (line.accounts?.length && (this.state.unfoldAll || line.default_unfolded)) {
                seeded[line.id] = line.accounts;
            }
        }
        this.state.accountLines = seeded;
        this.state.loading = false;
        this.saveSessionOptions();
        if (this.state.unfoldAll) {
            await this.unfoldAllLines();
        }
    }

    async onOpenUnpostedMoves() {
        const action = await this.orm.call("fs.report.engine", "open_unposted_moves", [
            this.options,
        ]);
        return this.action.doAction(action);
    }

    /**
     * Enterprise growth / report_line percent cell for a row.
     * @returns {{ name: string, mode: string }|null}
     */
    getGrowthComparison(row) {
        if (!this.showGrowthColumn || row.kind === "spacer") {
            return null;
        }
        const columns = row.columns || [];
        const greenOnPositive = row.green_on_positive !== false;
        if (this.state.compare === "report_line") {
            // Enterprise _compute_column_percent_comparison_data report_line:
            // round(value * 100 / base, 1); color vs 100.0 (float_compare digits=1).
            const base = this.baseReportLineValue;
            if (base === null || Math.abs(base) < 0.1) {
                return { name: _t("n/a"), mode: "muted" };
            }
            const value = columns[0] ?? 0;
            const percentage = Math.round((value * 100) / base * 10) / 10;
            const comparison = Math.round((percentage - 100) * 10);
            let mode = "";
            if (comparison !== 0) {
                mode = (comparison > 0) === greenOnPositive ? "green" : "red";
            }
            return { name: `${percentage.toFixed(1)}%`, mode };
        }
        if (columns.length < 2) {
            return null;
        }
        // Enterprise growth: descending → col0 vs col1; ascending → col1 vs col0.
        let firstValue;
        let secondValue;
        if (this.state.periodOrder === "descending") {
            firstValue = columns[0];
            secondValue = columns[1];
        } else {
            firstValue = columns[1];
            secondValue = columns[0];
        }
        const diff = firstValue - secondValue;
        const isAmount = this.state.growthDisplay === "amount";
        if (isAmount) {
            let mode = "muted";
            if (Math.abs(diff) >= 0.005) {
                // Enterprise: red if (values_diff > 0) XOR green_on_positive
                mode = (diff > 0) !== greenOnPositive ? "red" : "green";
            }
            return { name: this.formatAmount(diff), mode };
        }
        // Enterprise float_is_zero(value2, precision_rounding=0.1)
        if (Math.abs(secondValue) < 0.1) {
            return { name: _t("n/a"), mode: "muted" };
        }
        const growth = Math.round((diff / secondValue) * 1000) / 10;
        if (Math.abs(growth) < 0.05) {
            return { name: "0.0%", mode: "muted" };
        }
        return {
            name: `${growth.toFixed(1)}%`,
            mode: (diff > 0) !== greenOnPositive ? "red" : "green",
        };
    }

    getGrowthClasses(growth) {
        // Enterprise AccountReportLine.getGrowthComparisonClasses: text-end fw-bold + color.
        let classes = "o_fs_report_amount numeric line_cell o_column_percent_comparison text-end fw-bold";
        if (!growth || growth.mode === "muted") {
            classes += " muted";
        } else if (growth.mode === "green") {
            classes += " text-success";
        } else if (growth.mode === "red") {
            classes += " text-danger";
        }
        return classes;
    }

    async onToggleLine(line) {
        if (!line.unfoldable) {
            return;
        }
        if (this.state.accountLines[line.id]) {
            const next = { ...this.state.accountLines };
            delete next[line.id];
            this.state.accountLines = next;
            return;
        }
        if (line.accounts?.length) {
            this.state.accountLines = { ...this.state.accountLines, [line.id]: line.accounts };
            return;
        }
        const accounts = await this.orm.call("fs.report.engine", "get_account_lines", [
            line.id,
            this.options,
        ]);
        this.state.accountLines = { ...this.state.accountLines, [line.id]: accounts };
    }

    onOpenAccount(account) {
        return this.caretOpenGeneralLedger(account);
    }

    async caretOpenGeneralLedger(account) {
        const action = await this.orm.call(
            "fs.report.engine",
            "caret_option_open_general_ledger",
            [this.options, { account_id: account.id }]
        );
        return this.action.doAction(action);
    }

    async onExportPdf() {
        this.ui.block();
        try {
            await download({
                url: "/account_fs_report/export/pdf",
                data: {
                    report_id: this.reportId,
                    options: JSON.stringify(this.options),
                },
            });
        } finally {
            this.ui.unblock();
        }
    }

    async onExportXlsx() {
        this.ui.block();
        try {
            await download({
                url: "/account_fs_report/export/xlsx",
                data: {
                    report_id: this.reportId,
                    options: JSON.stringify(this.options),
                },
            });
        } finally {
            this.ui.unblock();
        }
    }
}

registry.category("actions").add("account_fs_report.main", FsReport);
