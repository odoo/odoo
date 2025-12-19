import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class PosOpenUIButton extends Component {
    static template = "point_of_sale.PosOpenUIButton";
    static props = {
        ...standardWidgetProps,
        action: { type: String },
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
    }

    // Visibility method intended to be overridden by other modules
    get isVisible() {
        return true;
    }

    /**
     * Used in pos.session and pos.config views.
     * Determines whether the POS is open based on available fields.
     */
    get isOpen() {
        const data = this.props.record.data;
        if ("current_session_state" in data) {
            return data.current_session_state === "opened";
        }

        return ["opening_control", "opened"].includes(data.state || data.rescue);
    }

    get label() {
        return this.isOpen ? _t("Continue Selling") : _t("Open Register");
    }

    // Always show the primary button on the dashboard.
    get class() {
        return "current_session_state" in this.props.record.data
            ? "btn btn-primary"
            : "btn btn-secondary";
    }

    async onClick(ev) {
        ev.preventDefault();

        const action = await this.orm.call(this.props.record.resModel, this.props.action, [
            this.props.record.resId,
        ]);

        if (!action) {
            return;
        }

        if (ev.ctrlKey || ev.metaKey || ev.button === 1) {
            action.target = "new";
        }

        await this.actionService.doAction(action, {
            onClose: async () => {
                await this.props.record.load();
            },
        });
    }
}

registry.category("view_widgets").add("pos_open_ui_button", {
    component: PosOpenUIButton,
    extractProps: ({ attrs }) => ({
        action: attrs.action,
    }),
});
