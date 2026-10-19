import { Component, t, useProps, xml } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { LazyComponent } from "@web/core/lazy_component";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class GlobalFilterWidgetLoader extends Component {
    static components = { LazyComponent };
    static template = xml`
        <LazyComponent
            bundle="'spreadsheet.o_spreadsheet'"
            Component="'spreadsheet_dashboard.GlobalFilterWidget'"
            props="this.props"
        />
    `;
    props = useProps({
        ...standardFieldProps,
        dashboard: t.string().optional(),
    });
}

registry.category("fields").add("global_filters", {
    component: GlobalFilterWidgetLoader,
    displayName: _t("Global Filters"),
    supportedOptions: [
        {
            label: _t("Dashboard"),
            name: "dashboard",
            type: "string",
        },
    ],
    supportedTypes: ["json"],
    isEmpty: () => false,
    extractProps({ options }) {
        return { dashboard: options.dashboard };
    },
});
