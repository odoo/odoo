import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";

export class PosOpenSessionStatistics extends Component {
    static template = "point_of_sale.pos_open_session_statistics";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    get data() {
        let data = this.props.record.data.statistics_for_current_session;

        if (!data) {
            // Demo data
            data = {
                session: {
                    is_open: true,
                    session_id: false,
                    demo: true,
                    nb_orders: 81,
                    name: "Demo Session/00001",
                },
                cash: { cash_control: true, raw_opening_cash: 0, opening_cash: "$ 193.10" },
                date: {
                    is_started: true,
                    is_ended: false,
                    start_date: "2025-08-12",
                    end_date: "Not ended yet",
                },
                orders: {
                    paid: { count: 41, total: "$ 999.00" },
                    refund: { count: 1, total: "$ 62.00" },
                    draft: { count: 34, total: "$ 860.00" },
                    cancel: { count: 5, total: "$ 230.00" },
                },
            };
        }

        return data;
    }

    async actionViewSession() {
        if (!this.data.session.session_id) {
            this.notification.add(_t("There are no sessions yet for this configuration."), {
                type: "warning",
            });
            return;
        }

        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "pos.session",
            res_id: this.data.session.session_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async actionViewOrders(type) {
        if (!this.data.session.session_id) {
            this.notification.add(_t("There are no sessions yet for this configuration."), {
                type: "warning",
            });
            return;
        }

        let domain = new Domain([["session_id", "=", this.data.session.session_id]]);
        switch (type) {
            case "paid":
                domain = Domain.and([domain, [["state", "=", "paid"]]]);
                break;
            case "refund":
                domain = Domain.and([domain, [["is_refund", "=", true]]]);
                break;
            case "draft":
                domain = Domain.and([domain, [["state", "=", "draft"]]]);
                break;
            case "cancel":
                domain = Domain.and([domain, [["state", "=", "cancel"]]]);
                break;
        }

        this.env.services.action.doAction({
            name: _t("Point of Sale orders"),
            type: "ir.actions.act_window",
            res_model: "pos.order",
            views: [[false, "list"]],
            target: "current",
            domain: domain.toList(),
        });
    }
}

export const posOpenSessionStatistics = {
    component: PosOpenSessionStatistics,
};

registry.category("view_widgets").add("pos_open_session_statistics", posOpenSessionStatistics);
