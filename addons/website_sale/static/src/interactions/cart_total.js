import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { CartTotal as CartTotalComponent } from '@website_sale/js/cart_total/cart_total';


export class CartTotal extends Interaction {
    static selector = 'div.o_cart_total';

    setup() {
        this.mountComponent(this.el, CartTotalComponent);
    }
}

registry.category('public.interactions').add('website_sale.total', CartTotal);
