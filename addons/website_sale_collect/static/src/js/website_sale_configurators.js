import {WebsiteSale} from '@website_sale/js/website_sale';

WebsiteSale.include({
    /**
     * When click and collect is activated allow adding a product in the cart via configurator.
     *
     * @override of `website_sale`
     */
    _getAdditionalDialogProps() {
        const props = this._super(...arguments);
        props.isClickAndCollectActive = Boolean(
            this.el.querySelector('.o_click_and_collect_availability')
        );
        return props;
    },
})
