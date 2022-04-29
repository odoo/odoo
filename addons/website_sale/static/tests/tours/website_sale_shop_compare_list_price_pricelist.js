/** @odoo-module **/

import tour from 'web_tour.tour';
import tourUtils from 'website_sale.tour_utils';

tour.register('compare_list_price_price_list_display', {
        test: true,
        url: '/shop?search=test_product'
    },
    [
        tourUtils.assertProductPrice("price_reduce", "1,000", "test_product_default"),
        tourUtils.assertProductPrice("price_reduce", "2,000", "test_product_with_compare_list_price"),
        tourUtils.assertProductPrice("base_price",   "2,500", "test_product_with_compare_list_price"),
        tourUtils.assertProductPrice("price_reduce", "2,000", "test_product_with_pricelist"),
        tourUtils.assertProductPrice("price_reduce", "4,000", "test_product_with_pricelist_and_compare_list_price"),
        tourUtils.assertProductPrice("base_price",   "4,500", "test_product_with_pricelist_and_compare_list_price"),

        ...tourUtils.selectPriceList('pricelist_with_discount'),

        tourUtils.assertProductPrice("price_reduce", "1,000", "test_product_default"),
        tourUtils.assertProductPrice("price_reduce", "2,000", "test_product_with_compare_list_price"),
        tourUtils.assertProductPrice("base_price",   "2,500", "test_product_with_compare_list_price"),
        tourUtils.assertProductPrice("price_reduce", "1,500", "test_product_with_pricelist"),
        tourUtils.assertProductPrice("price_reduce", "3,500", "test_product_with_pricelist_and_compare_list_price"),
        tourUtils.assertProductPrice("base_price",   "4,500", "test_product_with_pricelist_and_compare_list_price"),

        ...tourUtils.selectPriceList('pricelist_without_discount'),

        tourUtils.assertProductPrice("price_reduce", "1,000", "test_product_default"),
        tourUtils.assertProductPrice("price_reduce", "2,000", "test_product_with_compare_list_price"),
        tourUtils.assertProductPrice("base_price",   "2,500", "test_product_with_compare_list_price"),
        tourUtils.assertProductPrice("price_reduce", "1,500", "test_product_with_pricelist"),
        tourUtils.assertProductPrice("base_price",   "2,000", "test_product_with_pricelist"),
        tourUtils.assertProductPrice("price_reduce", "3,500", "test_product_with_pricelist_and_compare_list_price"),
        tourUtils.assertProductPrice("base_price",   "4,500", "test_product_with_pricelist_and_compare_list_price"),

    ]
);
