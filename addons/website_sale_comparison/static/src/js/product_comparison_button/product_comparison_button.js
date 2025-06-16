import { Component } from '@odoo/owl';
import { usePopover } from '@web/core/popover/popover_hook';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';
import { ProductComparisonPopover } from '../product_comparison_popover/product_comparison_popover';

export class ProductComparisonButton extends Component {
    static template = 'website_sale_comparison.ProductComparisonButton';
    static props = {
        bus: Object,
        currencyId: Number,
    };

    setup() {
        super.setup();
        this.popover = usePopover(ProductComparisonPopover);
    }

    togglePopover(ev) {
        this.popover.isOpen
            ? this.popover.open(ev.currentTarget, { bus: this.props.bus }) : this.popover.close();
    }

    get showButton() {
        const productIds = comparisonUtils.getComparisonProductIdsCookie();
        return productIds.length;
    }
}
