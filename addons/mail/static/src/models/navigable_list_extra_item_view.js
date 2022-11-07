/** @odoo-module **/

import { one, clear, Model } from '@mail/model';

/**
 * Models a relation between a NavigableListView and a
 * navigableListItemView where suggestable is used as iterating field for extra
 * suggestions.
 */
Model({
    name: 'NavigableListExtraItemView',
    fields: {
        navigableListMainOrExtraItemView: one('NavigableListMainOrExtraItemView',{ default:{}, inverse: 'extraItemViewOwner' }),
        navigableListViewOwner: one('NavigableListView', { identifying: true, inverse: 'extraItems' }),
        suggestable: one('Suggestable', { identifying: true, inverse: 'navigableListExtraItemViews' }),
    },
});
