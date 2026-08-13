import {
    MapContainer
} from '@delivery/js/location_selector/map_container/map_container';
import { patch } from '@web/core/utils/patch';
import { _t } from '@web/core/l10n/translation';

patch(MapContainer.prototype, {
    get errorMessage() {
        // The original definition of this getter is in `delivery` module which is not a frontend module. This problem happens in the context of the website. So, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("There was an error loading the map");
    },

    get chooseLocationButtonLabel() {
        // The original definition of this getter is in `delivery` module which is not a frontend module. This problem happens in the context of the website. So, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("Choose this location");
    },

    get openingHoursLabel() {
        // The original definition of this getter is in `delivery` module which is not a frontend module. This problem happens in the context of the website. So, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("Opening hours");
    },
});
