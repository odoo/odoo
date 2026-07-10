import { Component, props, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class PosSelfOpenKioskButton extends Component {
    static template = "pos_self_order.OpenKioskButton";
    props = props({
        ...standardWidgetProps,
        action: t.string(),
    });

    get isOpen() {
        return this.props.record.data.current_session_id;
    }

    get label() {
        return this.isOpen ? _t("Open Kiosk") : _t("Start Kiosk");
    }

    get class() {
        return this.isOpen ? "btn btn-secondary" : "btn btn-primary pos_open_session_btn";
    }

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
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
        await this.doAction(action);
    }

    async doAction(action) {
        return await this.actionService.doAction(action, {
            onClose: async () => {
                await this.props.record.load();
            },
        });
    }
}

registry.category("view_widgets").add("pos_self_open_kiosk_button", {
    component: PosSelfOpenKioskButton,
    extractProps: ({ attrs }) => ({
        action: attrs.action,
    }),
});
