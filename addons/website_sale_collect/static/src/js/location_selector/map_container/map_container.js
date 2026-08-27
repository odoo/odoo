import { deserializeDate, toLocaleDateString } from '@web/core/l10n/dates';
import { patch } from '@web/core/utils/patch';

import { MapContainer } from '@website_sale_stock/js/location_selector/map_container/map_container';

patch(MapContainer, {
    props: {
        ...MapContainer.props,
        taxRecomputationWarning: { type: String, optional: true },
    },
});

patch(MapContainer.prototype, {
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
