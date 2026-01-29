import { patch } from "@web/core/utils/patch";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { _t } from "@web/core/l10n/translation";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";

/**
 * @props partner
 */
patch(ActionpadWidget, {
    props: {
        ...ActionpadWidget.props,
        setTable: { type: Function, optional: true },
        assignOrder: { type: Function, optional: true },
    },
});

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup();
        this.doSubmitOrder = useTrackedAsync(() => this.pos.submitOrder());
        this.doReprintOrder = useTrackedAsync(() => this.pos.reprintOrder());
    },
    get swapButton() {
        return (
            this.pos.config.module_pos_restaurant &&
            this.pos.router.state.current !== "TicketScreen"
        );
    },
    get hasChangesToPrint() {
        return Boolean(this.displayCategoryCount.length);
    },
    hasQuantity(order) {
        if (!order) {
            return false;
        } else {
            return order.lines.reduce((totalQty, line) => totalQty + line.getQuantity(), 0) > 0;
        }
    },
    get highlightPay() {
        return (
            this.currentOrder?.lines?.length &&
            !this.hasChangesToPrint &&
            this.hasQuantity(this.currentOrder) &&
            !this.getCourseToFire()
        );
    },
    get displayCategoryCount() {
        return this.pos.categoryCount.slice(0, 4);
    },
    get isCategoryCountOverflow() {
        if (this.pos.categoryCount.length > 4) {
            return true;
        }
        return false;
    },
    get displayFireCourseBtn() {
        const order = this.currentOrder;
        if (order.isDirectSale || !order.hasCourses()) {
            return false;
        }
        return this.getCourseToFire() != null;
    },
    get fireCourseBtnText() {
        const selectedCourse = this.getCourseToFire();
        if (selectedCourse) {
            return _t("Fire %s", selectedCourse.name);
        }
        return "";
    },
    getCourseToFire() {
        const course = this.currentOrder.getSelectedCourse();
        if (course?.isReadyToFire()) {
            return course;
        }
    },
    async clickFireCourse() {
        const course = this.getCourseToFire();
        if (!course) {
            return;
        }
        this.currentOrder.cleanCourses(); //remove empty course on fire course.
        await this.pos.fireCourse(course);
        this.pos.showDefault();
    },
});
