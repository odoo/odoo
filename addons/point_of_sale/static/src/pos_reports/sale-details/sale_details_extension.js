import { Component, useProps, types as t } from "@odoo/owl";
import { reportExtensionRegistry, SLOT_LINE_NAME } from "../pos_report_plugin";

export class SaleDetailsLineExtension extends Component {
    static template = "pos_reports.SaleDetailsExtension";

    props = useProps({
        line: t.object(),
        depth: t.number().optional(0),
    });
}

reportExtensionRegistry.add(
    "sales_detail.line",
    {
        handler: "pos.sales.detail.report",
        slot: SLOT_LINE_NAME,
        component: SaleDetailsLineExtension,
    },
    { sequence: 10 }
);
