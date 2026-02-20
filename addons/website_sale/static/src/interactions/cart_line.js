import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { CartLines as CartLinesComponent } from '@website_sale/js/cart_lines/cart_lines';


export class CartLine extends Interaction {
    static selector = '#cart_products';

    setup() {
        const templateData = {
            removeButtonText: this.el.parentElement.querySelector('.cart_remove').textContent,
            wishlistButtonText: this.el.parentElement.querySelector('.cart_wishlist').textContent,
            qtyMinusButtonText: this.el.parentElement.querySelector('.cart_quantity_minus').textContent,
            qtyPlusButtonText: this.el.parentElement.querySelector('.cart_quantity_plus').textContent,
        }
        this.mountComponent(this.el, CartLinesComponent, { templateData });
    }
}

registry
    .category('public.interactions')
    .add('website_sale.cart_line', CartLine);
