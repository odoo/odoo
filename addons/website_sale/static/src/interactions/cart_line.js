import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { CartLines as CartLinesComponent } from '@website_sale/js/cart_lines/cart_lines';


export class CartLine extends Interaction {
    static selector = '#cart_products';

    setup(){
        this.mountComponent(this.el, CartLinesComponent);
    }
}

registry
    .category('public.interactions')
    .add('website_sale.cart_line', CartLine);
