import { Component, onWillStart, proxy, signal, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { formatDate, serializeDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";
import { getRoundingUnitNames, roundForUnit, roundingUnitLabel } from "../fs_report/rounding";

const { DateTime } = luxon;

export class FsGeneralLedger extends Component {
    static template = "account_fs_report.FsGeneralLedger";
    static components = { ControlPanel, Dropdown, DropdownItem };
    props = useProps(standardActionServiceProps);

    dateFromRef = signal.ref();
    dateToRef = signal.ref();

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.loadToken = 0;
        this.roundingUnitNames = getRoundingUnitNames("$");
        const params = this.props.action.params || {};
        const incoming = params.options || {};
        const ctx = this.props.action.context || {};
        const filterAccounts = incoming.filter_accounts || ctx.default_filter_accounts || "";
        this.state = proxy({
            loading: true,
            lines: [],
            currencyId: user.activeCompany.currency_id,
            hasUnposted: false,
            filterAccounts,
            accountIds: incoming.account_ids || [],
            dateFrom: incoming.date_from
                ? DateTime.fromISO(incoming.date_from)
                : DateTime.now().startOf("year"),
            dateTo: incoming.date_to
                ? DateTime.fromISO(incoming.date_to)
                : DateTime.now().startOf("day"),
            targetMove: incoming.target_move || "posted",
            journalIds: incoming.journal_ids || [],
            unfoldedAccountIds: incoming.unfolded_account_ids || [],
            searchInput: filterAccounts,
            roundingUnit: "decimals",
        });
        const component = this;
        this.dateFromPicker = useDateTimePicker({
            target: this.dateFromRef,
            get pickerProps() {
                return { value: component.state.dateFrom, type: "date" };
            },
            onApply: (date) => {
                if (!date) {
                    return;
                }
                this.state.dateFrom = date.startOf("day");
                this.reload();
            },
        });
        this.dateToPicker = useDateTimePicker({
            target: this.dateToRef,
            get pickerProps() {
                return { value: component.state.dateTo, type: "date" };
            },
            onApply: (date) => {
                if (!date) {
                    return;
                }
                this.state.dateTo = date.startOf("day");
                this.reload();
            },
        });
        onWillStart(async () => {
            const companies = await this.orm.read("res.company", [user.activeCompany.id], ["currency_id"]);
            if (companies[0]?.currency_id) {
                const currencies = await this.orm.read(
                    "res.currency",
                    [companies[0].currency_id[0]],
                    ["symbol"]
                );
                if (currencies[0]?.symbol) {
                    this.roundingUnitNames = getRoundingUnitNames(currencies[0].symbol);
                }
            }
            await this.reload();
        });
    }

    get companyIds() {
        const current = user.activeCompany;
        const ids = user.activeCompanies.map((company) => company.id);
        return [current.id, ...ids.filter((id) => id !== current.id)];
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

    formatDateValue(date) {
        return formatDate(date);
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

    async reload() {
        const token = ++this.loadToken;
        this.state.loading = true;
        const data = await this.orm.call("fs.general.ledger", "get_report_data", [this.options]);
        if (token !== this.loadToken) {
            return;
        }
        this.state.lines = data.lines;
        this.state.currencyId = data.currency_id;
        this.state.hasUnposted = data.has_unposted;
        this.state.loading = false;
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
    }

    openDateFromPicker() {
        this.dateFromPicker.open();
    }

    openDateToPicker() {
        this.dateToPicker.open();
    }

    onPrint() {
        window.print();
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

    async onOpenUnpostedMoves() {
        const action = await this.orm.call("fs.general.ledger", "open_unposted_moves", [
            this.options,
        ]);
        return this.action.doAction(action);
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
}

registry.category("actions").add("account_fs_report.general_ledger", FsGeneralLedger);
