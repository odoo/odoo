import { Component, useProps, proxy, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";


export class StockValuationReportLine extends Component {
    static template = "account.StockValuationReport.InventoryValuationLine";
    props = useProps({
        class: t.string().optional(),
        label: t.string().optional(),
        level: t.number().optional(0),
        line: t.object().optional(),
        sublines: t.array().optional(),
        onClickMethod: t.function().optional(),
        value: t.number().optional(),
    });

    setup() {
        this.hasSublines = Boolean(this.props.sublines?.length);
        this.state = proxy({ displaySublines: this.hasSublines });
    }

    // Getters -----------------------------------------------------------------
    get accounts() {
        if (! this.hasSublines) { return []; }
        return this.constructor.getLineAccounts(this.props.sublines);
    }

    // Account ids of `lines`, descending into nested sublines (e.g. the Accrual section's
    // per-accrual-type lines, whose own account is their nested lines' accounts).
    static getLineAccounts(lines) {
        return lines.flatMap(line =>
            line.lines?.length ? this.getLineAccounts(line.lines) : (line.account_id ? [parseInt(line.account_id)] : [])
        );
    }

    get credit() {
        if (this.props.line?.credit) {
            return this.env.formatMonetary(this.props.line.credit);
        }
        return false;
    }

    get cssClass() {
        let cssClass = this.props.class || "";
        cssClass += ` line_level_${this.props.level}`;
        return cssClass;
    }

    get debit() {
        if (this.props.line?.debit) {
            return this.env.formatMonetary(this.props.line.debit);
        }
        return false;
    }

    get displayTotalOnSeparateLine() {
        return Boolean(this.props.value && this.state.displaySublines);
    }

    get formattedValue() {
        if (this.props.value !== undefined) {
            return this.env.formatMonetary(this.props.value);
        }
        return false;
    }

    get label() {
        return this.props.label || this.props.line.account?.display_name;
    }

    get totalProps() {
        const props = {
            class: "total",
            label: _t("Total"),
            level: this.props.level,
            value: this.props.value,
        };
        if (this.props.onClickMethod) {
            props.onClickMethod = this.props.onClickMethod;
        }
        return props;
    }

    // On Click Methods --------------------------------------------------------
    onClick() {
        this.props.onClickMethod && this.props.onClickMethod(this.accounts);
    }

    onClickToggle() {
        if (this.props.sublines && this.props.sublines.length) {
            this.state.displaySublines = !this.state.displaySublines;
        }
    }
}

StockValuationReportLine.components = { StockValuationReportLine };
