import { t, useProps } from "@odoo/owl";
import { ComboConfiguratorDialog } from "@sale/js/combo_configurator_dialog/combo_configurator_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ComboConfiguratorDialog.prototype, {
    setup() {
        super.setup();

        this.websiteSaleProps = useProps({
            isFrontend: t.boolean().optional(),
            options: t
                .object({
                    isBuyNow: t.boolean().optional(),
                })
                .optional(),
        });

        if (this.websiteSaleProps.isFrontend) {
            this.getPriceUrl = "/website_sale/combo_configurator/get_price";
            this.getValuesUrl = "/website_sale/product_configurator/get_values";
        }
    },

    get totalMessage() {
        if (this.websiteSaleProps.isFrontend) {
            return _t("Total: %s", this.formattedTotalPrice);
        }
        return super.totalMessage(...arguments);
    },

    get _comboProductData() {
        const comboProductData = super._comboProductData;
        if (this.websiteSaleProps.isFrontend) {
            Object.assign(comboProductData, { price: this._comboPrice });
        }
        return comboProductData;
    },

    _getAdditionalDialogProps() {
        const props = super._getAdditionalDialogProps();
        if (this.websiteSaleProps.isFrontend) {
            props.isFrontend = this.websiteSaleProps.isFrontend;
        }
        return props;
    },
});
