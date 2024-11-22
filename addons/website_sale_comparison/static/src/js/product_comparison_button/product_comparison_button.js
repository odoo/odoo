import { Component, useState, useEffect, onMounted, onWillUnmount } from "@odoo/owl";
import { useBus } from '@web/core/utils/hooks';
import { usePopover } from '@web/core/popover/popover_hook';
import comparisonUtils from '@website_sale_comparison/js/website_sale_comparison_utils';
import { ProductComparisonPopover } from '../product_comparison_popover/product_comparison_popover';
import { debounce } from "@web/core/utils/timing";

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

        this.handleScroll = debounce(() => {
            if (this.popover.isOpen) {
                this.popover.close();
            }
        }, 100);
        onMounted(() => {
            window.addEventListener("scroll", this.handleScroll);
        });
        onWillUnmount(() => {
            window.removeEventListener("scroll", this.handleScroll);
        });
        useEffect(
            () => {
                // Once the productCount state is set, we check if the product
                // comparison button should be shown.
                // Trigger cookie bar overlap handling only when the product
                // count is 1, since that's when the compare button becomes
                // visible.
                if (this.state.productCount === 1) {
                    // Dispatch a custom event when the product comparison
                    // button is shown to handle the overlap with the cookies
                    // bar modal.
                    const cookieBarEl = document.querySelector("#website_cookies_bar");
                    cookieBarEl?.dispatchEvent(
                        new CustomEvent("COOKIES_BAR_SHOWN", { bubbles: true })
                    );
                }
            },
            () => [this.state.productCount]
        );
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
