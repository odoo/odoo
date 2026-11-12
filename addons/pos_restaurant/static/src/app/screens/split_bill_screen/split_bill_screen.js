import { SplitBillScreen } from "@point_of_sale/app/screens/split_bill_screen/split_bill_screen";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(SplitBillScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.isTransferred = false;
    },

    isSplitLineEligible(line) {
        if (!this.pos.config.module_pos_restaurant) {
            return super.isSplitLineEligible(...arguments);
        }
        return (
            line.product_id.id !== this.pos.config.discount_product_id?.id &&
            line.product_id.id !== this.currentOrder.preset_id?.service_fee_product_id?.id
        );
    },

    isSplitLineCountable(line) {
        if (!this.pos.config.module_pos_restaurant) {
            return super.isSplitLineCountable(...arguments);
        }
        return line.isGlobalDiscountApplicable();
    },

    prepareSplitOrder(originalOrder, newOrder) {
        if (!this.pos.config.module_pos_restaurant) {
            return super.prepareSplitOrder(...arguments);
        }
        return {
            ...super.prepareSplitOrder(...arguments),
            newCourses: new Map(),
            prepOrder: originalOrder.prep_order_ids?.length
                ? this.pos.models["pos.prep.order"].create({ pos_order_id: newOrder })
                : null,
            prepLinePairs: [],
        };
    },

    getSplitLineData(line, newOrder, splitContext) {
        const values = super.getSplitLineData(...arguments);
        if (!this.pos.config.module_pos_restaurant || !line.course_id) {
            return values;
        }

        const courseIndex = line.course_id.index;
        let course = splitContext.newCourses.get(courseIndex);
        if (!course) {
            course = this.pos.models["restaurant.order.course"].create({
                order_id: newOrder,
                index: courseIndex,
                name: _t("Course ") + courseIndex,
            });
            splitContext.newCourses.set(courseIndex, course);
        }
        return { ...values, course_id: course.id };
    },

    async afterSplitLineCreated(line, newLine, quantity, splitContext) {
        await super.afterSplitLineCreated(...arguments);
        if (!this.pos.config.module_pos_restaurant || !splitContext.prepOrder) {
            return;
        }

        let quantityToTransfer = quantity;
        for (const prepLine of line.prep_line_ids) {
            const preparedQuantity = prepLine.quantity - prepLine.cancelled;
            const transferredQuantity = Math.min(preparedQuantity, quantityToTransfer);
            if (transferredQuantity > 0) {
                const newPrepLine = this.pos.models["pos.prep.line"].create({
                    prep_order_id: splitContext.prepOrder,
                    pos_order_line_id: newLine,
                    product_id: prepLine.product_id.id,
                    quantity: transferredQuantity,
                    attribute_value_ids: prepLine.attribute_value_ids,
                });
                splitContext.prepLinePairs.push([prepLine.uuid, newPrepLine.uuid]);
                prepLine.quantity -= transferredQuantity;
                quantityToTransfer -= transferredQuantity;
            }
            if (!quantityToTransfer) {
                break;
            }
        }
    },

    async afterSplitOrderCreated(originalOrder, newOrder, splitContext) {
        await super.afterSplitOrderCreated(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            await this.pos.onPrepLinesSynced(splitContext.prepLinePairs);
        }
    },

    async beforeSplitOrderSync(originalOrder) {
        await super.beforeSplitOrderSync(...arguments);
        if (this.pos.config.module_pos_restaurant) {
            originalOrder.customer_count -= 1;
        }
    },

    shouldApplyDiscountToSplit() {
        return !this.isTransferred;
    },

    shouldRecomputeServiceFeeForSplit() {
        return !this.isTransferred;
    },

    async splitOrder() {
        await this.createSplittedOrder();
    },

    async transferSplittedOrder(event) {
        event.stopPropagation();
        const selectedQty = this.getNumberOfProducts();
        if (selectedQty > 0 && selectedQty !== this.totalOrderQuantity) {
            this.isTransferred = true;
            await this.createSplittedOrder();
        }
        this.pos.startTransferOrder();
    },
});
