import { Component, onWillDestroy, proxy, t, useProps } from "@odoo/owl";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { PriceFormatter } from "@point_of_sale/app/components/price_formatter/price_formatter";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";
import { localeCompare } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class SplitOrderLine extends Orderline {
    static template = Orderline.template;

    get lineScreenValues() {
        const values = super.lineScreenValues;
        return {
            ...values,
            unitPart: this.props.line.uiState.splitQty || values.unitPart,
        };
    }
}

export class SplitBillScreen extends Component {
    static template = "point_of_sale.SplitBillScreen";
    static components = { OrderDisplay, Orderline: SplitOrderLine, PriceFormatter };
    props = useProps({ orderUuid: t.string() });

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.qtyTracker = proxy({});
        this.priceTracker = proxy({});
        useRouterParamsChecker(this.constructor.name);
        onWillDestroy(() => {
            this.pos.models["pos.order.line"].map((line) => (line.uiState.splitQty = false));
        });
    }

    get currentOrder() {
        return this.pos.getOrder();
    }

    get newOrderPrice() {
        return Object.values(this.priceTracker).reduce((total, price) => total + price, 0);
    }

    getNumberOfProducts() {
        return Object.values(this.qtyTracker).reduce((total, quantity) => total + quantity, 0);
    }

    get totalOrderQuantity() {
        return this.currentOrder.lines.reduce(
            (total, line) => total + (this.isSplitLineCountable(line) ? line.qty : 0),
            0
        );
    }

    isSplitLineEligible(line) {
        return (
            line.product_id.id !== this.pos.config.discount_product_id?.id &&
            line.product_id.id !== this.pos.config.tip_product_id?.id &&
            !line.isServiceFeeLine()
        );
    }

    isSplitLineCountable(line) {
        return this.isSplitLineEligible(line) && line.isGlobalDiscountApplicable();
    }

    onClickLine(line) {
        const lines = line.getAllLinesInCombo();
        const rootQty = lines[0].getQuantity();
        for (const splitLine of lines) {
            const maxQty = splitLine.getQuantity();
            const currentQty = this.qtyTracker[splitLine.uuid] || 0;
            const selectedQty =
                splitLine.combo_parent_id && rootQty ? splitLine.getQuantity() / rootQty : 1;
            const nextQty =
                !splitLine.isPosGroupable() && !splitLine.isPartOfCombo()
                    ? currentQty === maxQty
                        ? 0
                        : maxQty
                    : currentQty === maxQty
                    ? 0
                    : Math.min(currentQty + selectedQty, maxQty);

            this.qtyTracker[splitLine.uuid] = nextQty;
            this.priceTracker[splitLine.uuid] =
                (splitLine.prices.total_included / maxQty) * nextQty;
            splitLine.uiState.splitQty = `${nextQty} / ${splitLine.getQuantityStr().unitPart}`;
        }
    }

    _getOrderName(order) {
        return order.table_id?.table_number.toString() || order.floatingOrderName || "";
    }

    _getSplitOrderName(name) {
        const latest =
            this.pos
                .getOpenOrders()
                .map((order) => this._getOrderName(order))
                .filter((orderName) => orderName.slice(0, -1) === name)
                .sort((a, b) => localeCompare(a.slice(-1), b.slice(-1)))
                .at(-1) || name;
        if (latest === name) {
            return `${name}B`;
        }
        const lastCharacter = latest.at(-1);
        if (lastCharacter === "Z") {
            throw new Error("You cannot split the order into more than 26 parts!");
        }
        return `${latest.slice(0, -1)}${String.fromCharCode(lastCharacter.charCodeAt(0) + 1)}`;
    }

    async paySplittedOrder() {
        const selectedQty = this.getNumberOfProducts();
        if (selectedQty > 0 && selectedQty < this.totalOrderQuantity) {
            const originalOrder = this.currentOrder;
            await this.createSplittedOrder();
            originalOrder.setScreenData({ name: "SplitBillScreen" });
        }
        this.pos.pay();
    }

    async createSplittedOrder() {
        const originalOrder = this.currentOrder;
        const newOrder = this.pos.createNewOrder({
            partner_id: originalOrder.partner_id,
            preset_id: originalOrder.preset_id,
            preset_time: originalOrder.preset_time,
            fiscal_position_id: originalOrder.fiscal_position_id,
            to_invoice: originalOrder.to_invoice,
            general_customer_note: originalOrder.general_customer_note,
            internal_note: originalOrder.internal_note,
        });
        newOrder.setPricelist(originalOrder.pricelist_id);
        newOrder.floating_order_name = this._getSplitOrderName(this._getOrderName(originalOrder));
        newOrder.uiState.splittedOrderUuid = originalOrder.uuid;
        originalOrder.uiState.splittedOrderUuid = newOrder.uuid;
        const splitContext = this.prepareSplitOrder(originalOrder, newOrder);

        const comboMap = new Map();
        const linesToDelete = [];
        for (const line of originalOrder.lines) {
            const quantity = this.qtyTracker[line.uuid];
            if (!quantity) {
                continue;
            }
            const data = { ...line.raw };
            delete data.combo_line_ids;
            delete data.combo_parent_id;
            delete data.course_id;
            delete data.prep_line_ids;
            delete data.uuid;
            delete data.id;
            const newLine = this.pos.models["pos.order.line"].create(
                {
                    ...data,
                    ...this.getSplitLineData(line, newOrder, splitContext),
                    qty: quantity,
                    order_id: newOrder.id,
                },
                false,
                true
            );
            newLine.setHasChange(false);
            if (line.combo_line_ids.length) {
                for (const comboLine of line.combo_line_ids) {
                    comboMap.set(comboLine.uuid, newLine);
                }
            }
            if (line.combo_parent_id) {
                newLine.combo_parent_id = comboMap.get(line.uuid);
            }
            await this.afterSplitLineCreated(line, newLine, quantity, splitContext);
            if (quantity === line.getQuantity()) {
                linesToDelete.push(line);
            } else {
                line.update({ qty: line.getQuantity() - quantity });
            }
        }
        for (const line of linesToDelete) {
            line.delete();
        }

        const { value, type } = originalOrder.globalDiscountPc;
        if (value) {
            await this.pos.applyDiscount(value, type, originalOrder);
            if (this.shouldApplyDiscountToSplit()) {
                await this.pos.applyDiscount(value, type, newOrder);
            }
        }
        if (originalOrder.preset_id?.service_fee) {
            originalOrder.recomputeServiceFees();
            if (this.shouldRecomputeServiceFeeForSplit()) {
                newOrder.recomputeServiceFees();
            }
        }

        originalOrder.setScreenData({ name: "ProductScreen" });
        await this.beforeSplitOrderSync(originalOrder, newOrder, splitContext);
        await this.pos.syncAllOrders({ orders: [originalOrder, newOrder] });
        await this.afterSplitOrderCreated(originalOrder, newOrder, splitContext);
        this.pos.selectedOrderUuid = null;
        this.pos.setOrder(newOrder);
        this.back();
        return newOrder;
    }

    back() {
        this.pos.navigate("ProductScreen", { orderUuid: this.pos.selectedOrderUuid });
    }

    adjustFontSize(amount) {
        const length = amount.toString().length;
        return length > 11 ? "6vw" : length > 9 ? "8vw" : "10vw";
    }

    prepareSplitOrder(_originalOrder, _newOrder) {
        return {};
    }

    getSplitLineData(_line, _newOrder, _splitContext) {
        return {};
    }

    async afterSplitLineCreated(_line, _newLine, _quantity, _splitContext) {}

    async beforeSplitOrderSync(_originalOrder, _newOrder, _splitContext) {}

    async afterSplitOrderCreated(_originalOrder, _newOrder, _splitContext) {}

    shouldApplyDiscountToSplit() {
        return true;
    }

    shouldRecomputeServiceFeeForSplit() {
        return true;
    }
}

registry.category("pos_pages").add("SplitBillScreen", {
    name: "SplitBillScreen",
    component: SplitBillScreen,
    route: `/pos/ui/${odoo.pos_config_id}/splitting/{string:orderUuid}`,
    params: { orderUuid: true, orderFinalized: false },
});
