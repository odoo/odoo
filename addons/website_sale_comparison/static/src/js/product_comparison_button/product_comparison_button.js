import { Component, useState } from '@odoo/owl';
import { useBus } from '@web/core/utils/hooks';
import { usePopover } from '@web/core/popover/popover_hook';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';
import { ProductComparisonPopover } from '../product_comparison_popover/product_comparison_popover';

export class ProductComparisonButton extends Component {
    static template = 'website_sale_comparison.ProductComparisonButton';
    static props = {
        bus: Object,
    };

    setup() {
        super.setup();
        this.state = useState({ productCount: comparisonUtils.getComparisonProductIds().length });
        this.popover = usePopover(ProductComparisonPopover, {
            env: { ...this.env, bus: this.props.bus },
            arrow: false,
            position: 'top',
        });
        useBus(
            this.props.bus,
            'comparison_products_changed',
            (_) => this.state.productCount = comparisonUtils.getComparisonProductIds().length,
        );
    }

    /**
     * Open or close the popover with the products to compare.
     *
     * @param {Event} ev
     */
    togglePopover(ev) {
        this.popover.isOpen ? this.popover.close() : this.popover.open(ev.currentTarget, {});
    }
}
