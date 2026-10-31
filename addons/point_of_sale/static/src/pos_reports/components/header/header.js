import { Component, useProps, types as t } from "@odoo/owl";

export class Header extends Component {
    static template = "pos_reports.Header";
    props = useProps({
        columns: t.array().optional([]),
        sectionName: t.string().optional(""),
    });
}
