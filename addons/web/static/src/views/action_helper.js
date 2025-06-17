import { Component } from "@odoo/owl";
import { Widget } from "@web/views/widgets/widget";
import { RibbonWidget } from "@web/views/widgets/ribbon/ribbon";

export class ActionHelper extends Component {
    static template = "web.ActionHelper";
    static components = { Widget, RibbonWidget };
    static props = {
        showRibbon: { type: Boolean, optional: true, default: false },
        noContentHelp: { type: String, optional: true },
    };

    get hasFacets() {
        return this.env.searchModel.facets.length > 0;
    }

    get showDefaultHelper() {
        return !this.props.noContentHelp;
    }

    showWidgetSampleData() {
        return this.props.showRibbon;
    }

    clearFilters() {
        this.env.searchModel.clearFilters();
    }
}
