import { t, useProps } from '@odoo/owl';
import { deserializeDate, toLocaleDateString } from '@web/core/l10n/dates';
import { patch } from '@web/core/utils/patch';

import { Location } from '@website_sale_stock/js/location_selector/location/location';

patch(Location.prototype, {
    setup() {
        super.setup();
        this.websiteSaleCollectProps = useProps({
            closingDates: t.array().optional(),
        });
    },

    /**
     * Format an ISO date string into a more human-readable format
     *
     * @param {String} isoDate - The date to format
     * @return {String} The formatted date.
     */
    formatClosingDate(isoDate) {
        return toLocaleDateString(deserializeDate(isoDate));
    },
});
