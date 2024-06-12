/** @odoo-module **/

import { formatFloat, formatFloatTime, formatMonetary } from "@web/views/fields/formatters";
import { Component } from "@odoo/owl";

export class BomOverviewSpecialLine extends Component {
    setup() {
        this.formatFloat = formatFloat;
        this.formatFloatTime = formatFloatTime;
        this.formatMonetary = (val) => formatMonetary(val, { currencyId: this.data.currency_id });
    }

    //---- Getters ----

    get data() {
        return this.props.data;
    }

    get precision() {
        return this.props.precision;
    }

    get hasFoldButton() {
        return ["operations", "byproducts"].includes(this.props.type);
    }

    get showAvailabilities() {
        return this.props.showOptions.availabilities;
    }

    get showCosts() {
        return this.props.showOptions.costs;
    }

    get showLeadTimes() {
        return this.props.showOptions.leadTimes;
    }

    get showUom() {
        return this.props.showOptions.uom;
    }

    get showAttachments() {
        return this.props.showOptions.attachments;
    }
}

BomOverviewSpecialLine.template = "mrp.BomOverviewSpecialLine";
BomOverviewSpecialLine.props = {
    type: String,
    isFolded: { type: Boolean, optional: true },
    showOptions: {
        type: Object,
        shape: {
            availabilities: Boolean,
            costs: Boolean,
            operations: Boolean,
            leadTimes: Boolean,
            uom: Boolean,
            attachments: Boolean,
        },
    },
    data: Object,
    precision: Number,
    toggleFolded: { type: Function, optional: true },
};
BomOverviewSpecialLine.defaultProps = {
    isFolded: true,
    toggleFolded: () => {},
};
