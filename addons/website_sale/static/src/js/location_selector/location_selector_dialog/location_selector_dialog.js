/** @odoo-module **/

import {
    LocationSelectorDialog
} from '@delivery/js/location_selector/location_selector_dialog/location_selector_dialog';
import { patch } from '@web/core/utils/patch';
import { _t } from '@web/core/l10n/translation';

patch(LocationSelectorDialog, {
    props: {
        ...LocationSelectorDialog.props,
        orderId: { type: Number, optional: true },
        isFrontend: { type: Boolean, optional: true },
    },
});

patch(LocationSelectorDialog.prototype, {
    setup() {
        super.setup(...arguments);

        if (this.props.isFrontend) {
            this.getLocationUrl = '/website_sale/get_pickup_locations';
        }
    },

    get title() {
        // The original definition of this getter is in `delivery` module which is not a frontend module. This problem happens in the context of the website. So, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("Choose a pick-up point");
    },

    get validationButtonLabel() {
        // The original definition of this getter is in `delivery` module which is not a frontend module. This problem happens in the context of the website. So, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("Choose this location");
    },

    get postalCodePlaceholder() {
        // The original definition of this getter is in `delivery` module which is not a frontend module. This problem happens in the context of the website. So, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("Your postal code");
    },

    get listViewButtonLabel() {
        // The original definition of this getter is in `delivery` module which is not a frontend module. This problem happens in the context of the website. So, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("List view");
    },

    get mapViewButtonLabel() {
        // The original definition of this getter is in `delivery` module which is not a frontend module. This problem happens in the context of the website. So, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("Map view");
    },

    get errorMessage() {
        // The original definition of this getter is in `delivery` module which is not a frontend module. This problem happens in the context of the website. So, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("No result");
    },

    get loadingMessage() {
        // The original definition of this getter is in `delivery` module which is not a frontend module. This problem happens in the context of the website. So, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("Loading...");
    },
});
