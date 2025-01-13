import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.AddToCartSnippet = publicWidget.Widget.extend({
    selector: '.s_add_to_cart_btn',
    events: {
        'click': '_onClickAddToCartButton',
    },

    init() {
        this._super(...arguments);
        this.notification = this.bindService("notification");
    },

    _onClickAddToCartButton: async function (ev) {
        const dataset = ev.currentTarget.dataset;

        const productTemplateId = parseInt(dataset.productTemplateId);
        const productId = parseInt(dataset.productVariantId);
        const isCombo = dataset.isCombo === 'true';
        const action = dataset.action;

        if (productId) {
            const isAddToCartAllowed = await rpc(`/shop/product/is_add_to_cart_allowed`, {
                product_id: productId,
            });
            if (!isAddToCartAllowed) {
                this.notification.add(
                    _t('This product does not exist therefore it cannot be added to cart.'),
                    { title: 'User Error', type: 'warning' }
                );
                return;
            }
        }

        this.call('cart', 'add',
            {
                productTemplateId: productTemplateId,
                productId: productId,
                isCombo: isCombo,
            },
            {
                isBuyNow: action === 'buy_now',
            }
        );
    },
});

export default publicWidget.registry.AddToCartSnippet;
