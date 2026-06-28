import { formatFloat, formatFloatTime, formatMonetary } from "@web/views/fields/formatters";
import { Component, props, t } from "@odoo/owl";

export class BomOverviewSpecialLine extends Component {
    static template = "mrp.BomOverviewSpecialLine";
    props = props({
        type: t.string(),
        isFolded: t.boolean().optional(true),
        showOptions: t.object({
            mode: t.string(),
            uom: t.boolean(),
            attachments: t.boolean(),
        }),
        data: t.object(),
        precision: t.number(),
        toggleFolded: t.function().optional(() => () => {}),
    });

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

    get forecastMode() {
        return this.props.showOptions.mode == "forecast";
    }

    get showUom() {
        return this.props.showOptions.uom;
    }

    get showAttachments() {
        return this.data.has_attachments;
    }
}
