/** @odoo-module **/

import { _t } from '@web/core/l10n/translation';
import { patch } from '@web/core/utils/patch';
import {
    ComboConfiguratorDialog
} from '@sale/js/combo_configurator_dialog/combo_configurator_dialog';

patch(ComboConfiguratorDialog, {
    props: {
        ...ComboConfiguratorDialog.props,
        isFrontend: { type: Boolean, optional: true },
        // The following fields are needed for tracking.
        category_name: { type: String, optional: true },
        currency_name: { type: String, optional: true },
    },
});

patch(ComboConfiguratorDialog.prototype, {
    setup() {
        super.setup(...arguments);

        if (this.props.isFrontend) {
            this.getPriceUrl = '/website_sale/combo_configurator/get_price';
        }
    },

    get totalMessage() {
        if (this.props.isFrontend) {
            return _t("Total: %s", this.formattedTotalPrice);
        }
        return super.totalMessage(...arguments);
    },

    get _comboProductData() {
        const comboProductData = super._comboProductData;
        if (this.props.isFrontend) {
            Object.assign(comboProductData, { 'price': this._comboPrice });
        }
        return comboProductData;
    },

    _getAdditionalDialogProps() {
        const props = super._getAdditionalDialogProps();
        if (this.props.isFrontend) {
            props.isFrontend = this.props.isFrontend;
        }
        return props;
    },
});
