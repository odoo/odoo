import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SelectPartnerButton } from "@point_of_sale/app/screens/product_screen/control_buttons/select_partner_button/select_partner_button";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.alert = useService("alert");
        this.printer = useService("printer");
    },
    clickTableGuests() {
        this.pos.setCustomerCount();
    },
    clickTransferOrder() {
        this.dialog.closeAll();
        this.pos.startTransferOrder();
    },
    showTransferCourse() {
        const order = this.currentOrder;
        if (!order || !order.hasCourses()) {
            return false;
        }
        return order.getSelectedCourse() || order.getSelectedOrderline();
    },
    openSplitPage() {
        this.pos.navigate("SplitBillScreen", {
            orderUuid: this.currentOrder.uuid,
        });
    },
    async clickTransferCourse() {
        this.dialog.closeAll();
        await this.pos.transferLinesToCourse();
    },
});
patch(ControlButtons, {
    components: {
        ...ControlButtons.components,
        SelectPartnerButton,
    },
});
