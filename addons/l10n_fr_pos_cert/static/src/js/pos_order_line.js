import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { patch } from "@web/core/utils/patch";

patch(PosOrderline.prototype, {
    get showOldUnitPrice() {
        return (
            this.price_type === "manual" &&
            !this.is_reward_line &&
            !this.isTipLine() &&
            !this._isGiftCardOrEWalletLine &&
            !this.settled_order_id &&
            !this.settled_invoice_id &&
            !this.sale_order_origin_id &&
            !this.event_ticket_id &&
            this.product_id.id !== this.config.deposit_product_id?.id &&
            (!this.config.module_pos_discount ||
                this.product_id.id !== this.config.discount_product_id?.id)
        );
    },
    get _isGiftCardOrEWalletLine() {
        if (this._e_wallet_program_id) {
            return true;
        }
        const specialProductIds = this.config._pos_special_display_products_ids || [];
        return specialProductIds.includes(this.product_id.product_tmpl_id.id);
    },
});
