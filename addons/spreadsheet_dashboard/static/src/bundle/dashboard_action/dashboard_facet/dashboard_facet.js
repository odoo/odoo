import { Component, t, useProps } from "@odoo/owl";

export class DashboardFacet extends Component {
    static template = "spreadsheet_dashboard.DashboardFacet";
    static components = {};

    props = useProps({
        facet: t.object(),
        clearFilter: t.function(),
        onClick: t.function(),
    });
}
