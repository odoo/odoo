/** @odoo-module alias=point_of_sale.Orderline **/

import PosComponent from 'point_of_sale.PosComponent';
import { float_is_zero } from 'web.utils';

/**
 * @emits 'select-orderline' @param {'pos.order.line'}
 * @emits 'click-lot' @param {'pos.order.line'}
 */
class Orderline extends PosComponent {
    onClickOrderline(orderline) {
        this.trigger('select-orderline', orderline);
    }
    getDisplayUnitPrice(orderlinePrices) {
        return this.env.model.config.iface_tax_included === 'subtotal'
            ? orderlinePrices.noTaxUnitPrice
            : orderlinePrices.withTaxUnitPrice;
    }
    /**
     * In order to properly cross-out the lst price when pricelist's `discount_policy` is `without_discount`,
     * we need to make sure that the unit price is comparable to the list price. The value of the displayed
     * unit price is based on `iface_tax_included` of the config. Therefore, we also compute the tax/untaxed
     * list price for it to be truly comparable to the display unit price of the orderline.
     * @see showListPrice
     * @param {'pos.order.line'} orderline
     */
    getProductLstPrice(orderline) {
        const order = this.env.model.getRecord('pos.order', orderline.order_id);
        const taxes = this.env.model.getFiscalPositionTaxes(
            this.env.model.getOrderlineTaxes(orderline),
            order.fiscal_position_id
        );
        const product = this.env.model.getRecord('product.product', orderline.product_id);
        const [withoutTax, withTax] = this.env.model.getUnitPrices(product.lst_price, taxes);
        return this.env.model.config.iface_tax_included === 'subtotal' ? withoutTax : withTax;
    }
    getIsOrderlineTracked(orderline) {
        const product = this.env.model.getRecord('product.product', orderline.product_id);
        return (
            product.tracking !== 'none' &&
            (this.env.model.pickingType.use_create_lots || this.env.model.pickingType.use_existing_lots)
        );
    }
    getOrderlineHasValidLots(orderline) {
        const product = this.env.model.getRecord('product.product', orderline.product_id);
        return product.tracking === 'serial'
            ? orderline.qty === orderline.pack_lot_ids.length
            : orderline.pack_lot_ids.length === 1;
    }
    getLotText(lot) {
        const orderline = this.env.model.getRecord('pos.order.line', lot.pos_order_line_id);
        const product = this.env.model.getRecord('product.product', orderline.product_id);
        const template = product.tracking === 'serial' ? this.env._t('SN %s') : this.env._t('Lot %s');
        return _.str.sprintf(template, lot.lot_name);
    }
    showListPrice(orderline, displayUnitPrice, lstPrice) {
        return (
            this.env.model.getDiscountPolicy(orderline) == 'without_discount' &&
            this.env.model.monetaryLT(displayUnitPrice, lstPrice)
        );
    }
    getFormattedProductLstPrice(lstPrice) {
        return this.env.model.formatCurrency(lstPrice, 'Product Price');
    }
    getFormattedDisplayUnitPrice(displayUnitPrice) {
        return this.env.model.formatCurrency(displayUnitPrice, 'Product Price');
    }
    getLotLines(orderline) {
        return orderline.pack_lot_ids.map((id) => this.env.model.getRecord('pos.pack.operation.lot', id));
    }
}
Orderline.template = 'point_of_sale.Orderline';

export default Orderline;
