import { models } from "@web/../tests/web_test_helpers";

const products = [
    {
        section_id: "product",
        record_id: 1,
        name: "Coffee",
        foldability: "static",
        values: {
            qty: 1,
            amount_total: 9,
            discount: 10,
            uom: "kg",
            combo_label: " (Milk, Sugar)",
        },
        lines: [],
    },
    {
        section_id: "product",
        record_id: 2,
        name: "Tea",
        foldability: "static",
        values: { qty: 1, amount_total: 9, discount: 0, uom: false },
        lines: [],
    },
];

const sales = {
    section_id: "sales",
    record_id: null,
    name: "Sales",
    foldability: "expanded",
    columns: [
        { id: "qty", label: "Qty", type: "quantity", align: "right", digits: 2 },
        { id: "amount_total", label: "Total", type: "monetary", align: "right" },
    ],
    values: { qty: 2, amount_total: 18 },
    lines: [
        {
            section_id: "category",
            record_id: 1,
            name: "Not Categorized",
            foldability: "collapsed",
            values: { qty: 2, amount_total: 18 },
            lines: [],
        },
    ],
};

export class PosReport extends models.ServerModel {
    _name = "pos.report";

    get_report_info(reportId) {
        const [report] = this.browse(reportId);
        return {
            id: report.id,
            name: report.name,
            handler: report.handler_model_name,
            filters: [
                { type: "date_range", key: "date_range", default: "month" },
                {
                    type: "multi_select",
                    key: "config_ids",
                    model: "pos.config",
                    label: "Point of Sale",
                },
                {
                    type: "single_select",
                    key: "session_id",
                    model: "pos.session",
                    label: "Session",
                    domain: [["config_id", "in", "config_ids"]],
                },
            ],
        };
    }

    get_report_data(reportId, { options } = {}) {
        const [report] = this.browse(reportId);
        const section = structuredClone(sales);
        if (options.unfold_all) {
            section.lines[0].foldability = "expanded";
            section.lines[0].lines = structuredClone(products);
        }
        return {
            report_name: report.name,
            currency: { id: 1, symbol: "$", position: "before", decimal_places: 2 },
            sections: [section],
        };
    }

    get_unfold_data(reportId, { options, section_id } = {}) {
        return {
            section_id,
            lines: structuredClone(
                section_id === "category" && options.record_id === 1 ? products : []
            ),
        };
    }

    _records = [
        {
            id: 1,
            name: "Sales Details",
            handler_model_name: "pos.sales.detail.report",
        },
    ];
}
