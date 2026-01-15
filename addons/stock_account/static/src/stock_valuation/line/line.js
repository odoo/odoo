import { Component, useState } from "@odoo/owl";


export class StockValuationReportLine extends Component {
    static template = "stock_account.StockValuationReport.InventoryValuationLine";
    static props = {
        class: { type: String, optional: true },
        displayDebitCredit: { type: Boolean, optional: true },
        label: { type: String, optional: true },
        level: { type: Number, optional: true },
        line: { type: Object, optional: true },
        sublines: { type: Array, optional: true },
        onClickMethod: { type: Function, optional: true },
        value: { type: Number, optional: true },
    };
    static defaultProps = {
        level: 0,
    };

    setup() {
        this.hasSublines = Boolean(this.props.sublines?.length);
        this.state = useState({ displaySublines: this.hasSublines });
    }

    // Getters -----------------------------------------------------------------
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
            label: this.env._t("Total"),
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
        this.props.onClickMethod && this.props.onClickMethod(this.props.line);
    }

    onClickToggle() {
        if (this.props.sublines && this.props.sublines.length) {
            this.state.displaySublines = !this.state.displaySublines;
        }
    }
}

StockValuationReportLine.components = { StockValuationReportLine };
