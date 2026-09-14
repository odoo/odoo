/** @odoo-module native */
import { Component, useEffect, useState } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { useService } from "@web/core/utils/hooks";
const log = makeLogger("pos.component.product_card");

const STOCK_BADGE_POSITION_CLASSES = {
    top_left: "top-0 start-0",
    top_right: "top-0 end-0",
    bottom_left: "bottom-0 start-0",
    bottom_right: "bottom-0 end-0",
};

export class ProductCard extends Component {
    static template = "point_of_sale.ProductCard";
    static props = {
        class: { type: String, optional: true },
        name: String,
        product: Object,
        productId: [Number, String],
        comboExtraPrice: { type: String, optional: true },
        color: { type: [Number, undefined], optional: true },
        imageUrl: [String, Boolean],
        onClick: { type: Function, optional: true },
        onMouseLeave: { type: Function, optional: true },
        showWarning: { type: Boolean, optional: true },
        productCartQty: { type: [Number, undefined], optional: true },
        slots: { type: Object, optional: true },
        isComboPopup: { type: Boolean, optional: true },
    };
    static defaultProps = {
        onClick: () => {},
        onMouseLeave: () => {},
        class: "",
        showWarning: false,
        isComboPopup: false,
    };

    setup() {
        useLifecycleLog(log);
        this.pos = useService("pos");
        this.posStock = useService("pos_stock");
        this.stockQuantities = useState(this.posStock.quantities);
        useEffect(
            () => {
                if (this.pos.config.show_stock_in_pos) {
                    this.posStock.request(this.stockProductIds);
                }
            },
            () => [this.pos.config.show_stock_in_pos, ...this.stockProductIds],
        );
    }

    onKeydown(event) {
        if (
            event.target !== event.currentTarget ||
            !["Enter", " "].includes(event.key)
        ) {
            return;
        }
        event.preventDefault();
        if (!event.repeat) {
            log.logic("keyboard activation", () => ({
                productId: this.props.productId,
                key: event.key,
            }));
            this.props.onClick(event);
        }
    }

    get productQty() {
        return this.env.utils.formatProductQty(this.props.productCartQty ?? 0, false);
    }

    get stockProductIds() {
        const product = this.props.product;
        return (
            product.product_variant_ids?.map((variant) => variant.id) ?? [product.id]
        );
    }

    get stockQuantity() {
        let total = 0;
        for (const id of this.stockProductIds) {
            const qty = this.stockQuantities[id];
            if (qty === undefined || qty === null) {
                return qty;
            }
            total += qty;
        }
        return total;
    }

    get stockBadge() {
        const config = this.pos.config;
        if (!config.show_stock_in_pos) {
            return null;
        }
        const qty = this.stockQuantity;
        const positionClass =
            STOCK_BADGE_POSITION_CLASSES[config.stock_display_location] ??
            STOCK_BADGE_POSITION_CLASSES.top_left;
        if (qty === undefined) {
            return {
                text: "…",
                statusClass: "o_pos_stock_loading text-bg-light",
                positionClass,
            };
        }
        if (qty === null) {
            return {
                text: "?",
                statusClass: "o_pos_stock_unknown text-bg-secondary",
                positionClass,
            };
        }
        const text = this.env.utils.formatProductQty(qty, false);
        if (qty <= 0) {
            return {
                text,
                statusClass: "o_pos_stock_empty text-bg-danger",
                positionClass,
            };
        }
        if (qty < config.low_stock_threshold) {
            return {
                text,
                statusClass: "o_pos_stock_low text-bg-warning",
                positionClass,
            };
        }
        return {
            text,
            statusClass: "o_pos_stock_available text-bg-success",
            positionClass,
        };
    }
}
