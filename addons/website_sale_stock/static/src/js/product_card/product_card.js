import { t, useProps } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import { ProductCard } from '@sale/js/product_card/product_card';

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        this.stockProps = useProps({
            quantity: t.number().optional(),
        });
        this.allQuantitySelectedTooltip = _t("All available quantity selected");
    },
});
