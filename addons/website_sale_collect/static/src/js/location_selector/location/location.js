import { patch } from '@web/core/utils/patch';

import { Location } from '@website/components/location_selector/location/location';

patch(Location, {
    props: {
        ...Location.props,
        additionalData: { type: Object, optional: true },
    },
});
