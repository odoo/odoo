import {
    Location
} from '@delivery/js/location_selector/location/location';
import { patch } from '@web/core/utils/patch';
import { _t } from '@web/core/l10n/translation';

patch(Location.prototype, {
    get openingHoursLabel() {
        // The original definition of this getter is in `delivery` module which is not a frontend module. This problem happens in the context of the website. So, it should be repeated here as translations are only fetched in the context of a frontend module, which is `website_sale` in this case.
        return _t("Opening hours");
    },
});
