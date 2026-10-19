import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { SelectPartnerButton } from "@point_of_sale/app/screens/product_screen/control_buttons/select_partner_button/select_partner_button";
import { patch } from "@web/core/utils/patch";

patch(ControlButtons.prototype, {
    setup() {
        super.setup(...arguments);
        this.alert = this.pos.alert;
    },
    clickTableGuests() {
        this.pos.setCustomerCount();
    },
    clickTransferOrder() {
        this.dialog.closeAll();
        this.pos.startTransferOrder();
    },
    get showAddCourse() {
        return (
            this.pos.config.module_pos_restaurant &&
            !this.props.showRemainingButtons &&
            !this.pos.getOrder()?.isRefund &&
            !this.pos.config.use_course_allocation
        );
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
        this.currentOrder.cleanCourses();
    },
});
patch(ControlButtons, {
    components: {
        ...ControlButtons.components,
        SelectPartnerButton,
    },
});
