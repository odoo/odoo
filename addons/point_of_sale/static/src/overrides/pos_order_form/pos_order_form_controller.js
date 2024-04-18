import { useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { registry } from "@web/core/registry";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { formView } from "@web/views/form/form_view";
import { StatusBarButtons } from "@web/views/form/status_bar_buttons/status_bar_buttons";

class PosOrderFormController extends FormController {
    static template = "point_of_sale.PosOrderFormView";
    setup() {
        super.setup();
        this.pos = usePos();
        this.pos.ticketScreenOrderId = this.props.resId;
    }
}
class PosOrderStatusBarButtons extends StatusBarButtons {
    static template = "point_of_sale.PosOrderStatusBarButtons";
    setup() {
        super.setup();
        this.pos = usePos();
        this.posState = useState({
            isPayable: false,
        });
        this.getOrder().then((order) => {
            this.posState.isPayable = order.state === "draft";
            this.posState.order = order;
        });
    }
    async print() {
        this.pos.printReceipt(await this.getOrder());
    }
    async getOrder() {
        const order = (await this.pos.data.read("pos.order", [this.pos.ticketScreenOrderId]))[0];
        this.pos.data.read(
            "pos.order.line",
            order.lines.filter((line) => typeof line.raw.refunded_orderline_id === "number")
        );
        return order;
    }
    async loadOrder() {
        const order = await this.getOrder();
        this.pos.set_order(order);
        this.pos.showScreen("ProductScreen");
    }
    async refund() {
        const order = await this.getOrder();
        const refundOrdersIds = await this.pos.data.call("pos.order", "refund", [order.id]);
        const refundOrder = (await this.pos.data.read("pos.order", refundOrdersIds))[0];
        this.pos.set_order(refundOrder);
        this.pos.showScreen("ProductScreen");
    }
}

class PosOrderFormRenderer extends FormRenderer {
    static components = {
        ...FormRenderer.components,
        StatusBarButtons: PosOrderStatusBarButtons,
    };
}
export const posOrderFormController = {
    ...formView,
    Controller: PosOrderFormController,
    Renderer: PosOrderFormRenderer,
};

registry.category("views").add("pos_order_form", posOrderFormController);
