import { patch } from '@web/core/utils/patch';

import { MapContainer } from '@delivery/js/location_selector/map_container/map_container';

patch(MapContainer, {
    props: {
        ...MapContainer.props,
        taxRecomputationWarning: { type: String, optional: true },
    },
});
