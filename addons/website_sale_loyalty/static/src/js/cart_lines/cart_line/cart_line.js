import { CartLine } from '@website_sale/js/cart_lines/cart_line/cart_line';
import { patch } from '@web/core/utils/patch';
import { formatDate } from '@web/core/l10n/dates';


patch(CartLine, {
    props: {
        ...CartLine.props,
        isRewardLine: { type: Boolean },
        showCouponCode: { type: Boolean },
        couponCode: { type: String, optional: true },
        couponExpirationDate: { type: String, optional: true },
        rewardType: { type: String, optional: true },
    },
});

patch(CartLine.prototype, {
    formatDate(date) {
        const formattedDate = luxon.DateTime.fromISO(date);
        return formatDate(formattedDate);
    },
});