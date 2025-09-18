// @ts-check

/** @module @web/views/action_helper - Empty-state placeholder shown when a view has no records */

import { Component } from "@odoo/owl";
import { RibbonWidget } from "@web/views/widgets/ribbon/ribbon";
import { Widget } from "@web/views/widgets/widget";

/** Empty-state placeholder shown when a view has no records (onboarding helper / ribbon). */
export class ActionHelper extends Component {
    static template = "web.ActionHelper";
    static components = { Widget, RibbonWidget };
    static props = {
        showRibbon: { type: Boolean, optional: true, default: false },
        noContentHelp: { type: String, optional: true },
    };

    get showDefaultHelper() {
        return !this.props.noContentHelp;
    }
}
