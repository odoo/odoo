import { Component, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Help } from "@web/views/help/help";

export class ActionHelper extends Component {
    static template = "web.ActionHelper";
    static components = { Help };
    props = useProps({
        noContentHelp: t.string().optional(),
    });

    /**
     * Help of the action, or a default text if the action has no help.
     */
    get actionHelp() {
        return this.props.noContentHelp || _t("No data to display");
    }

    /**
     * Help view (see `help_id` view attribute), inlined in the view arch.
     */
    get helpArchInfo() {
        return this.env.config.noContentHelpArchInfo;
    }
}
