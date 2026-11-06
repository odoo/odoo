import { formatFloat, formatMonetary } from "@web/views/fields/formatters";
import { BomOverviewLine } from "../bom_overview_line/mrp_bom_overview_line";
import { BomOverviewComponentsBlock } from "../bom_overview_components_block/mrp_bom_overview_components_block";
import { Component, t, useProps, usePlugin } from "@odoo/owl";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";

export class BomOverviewTable extends Component {
    static template = "mrp.BomOverviewTable";
    static components = {
        BomOverviewLine,
        BomOverviewComponentsBlock,
    };
    props = useProps({
        showOptions: t.object({
            mode: t.string(),
            uom: t.boolean(),
            attachments: t.boolean(),
        }),
        uomName: t.string().optional(),
        currentWarehouseId: t.number().optional(),
        data: t.object(),
        precision: t.number(),
        bomQuantity: t.number(),
        changeFolded: t.function(),
    });

    setup() {
        this.actionService = usePlugin(ActionPlugin);
        this.formatFloat = formatFloat;
        this.formatMonetary = (val) => formatMonetary(val, { currencyId: this.data.currency_id });
    }

    //---- Handlers ----

    //---- Getters ----

    get data() {
        return this.props.data;
    }

    get precision() {
        return this.props.precision;
    }

    get forecastMode() {
        return this.props.showOptions.mode == "forecast";
    }

    get showUnitCosts() {
        return this.props.bomQuantity > 0;
    }

    get showUom() {
        return this.props.showOptions.uom;
    }

    get showAttachments() {
        return this.props.showOptions.attachments;
    }
}
