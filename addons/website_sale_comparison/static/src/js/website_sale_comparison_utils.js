import { cookie } from '@web/core/browser/cookie';

const COMPARISON_PRODUCT_IDS_COOKIE_NAME = 'comparison_product_ids';
const MAX_COMPARISON_PRODUCTS = 4;

function getComparisonProductIdsCookie() {
    return JSON.parse(cookie.get(COMPARISON_PRODUCT_IDS_COOKIE_NAME) || '[]');
}

function setComparisonProductIdsCookie(productIds) {
    cookie.set(COMPARISON_PRODUCT_IDS_COOKIE_NAME, JSON.stringify(Array.from(productIds)));
}

export default {
    getComparisonProductIdsCookie: getComparisonProductIdsCookie,
    setComparisonProductIdsCookie: setComparisonProductIdsCookie,
    MAX_COMPARISON_PRODUCTS: MAX_COMPARISON_PRODUCTS,
};
