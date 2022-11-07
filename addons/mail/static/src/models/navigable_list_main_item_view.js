/** @odoo-module **/

import { one, Model } from '@mail/model';

/**
 * Models a relation between a NavigableListView and a
 * navigableListItemView where suggestable is used as iterating field for main
 * suggestions.
 */
Model({
    name: 'NavigableListMainItemView',
    fields: {
        navigableListMainOrExtraItemView: one('NavigableListMainOrExtraItemView',{ default: {}, inverse: 'mainItemViewOwner' }),
        navigableListViewOwner: one('NavigableListView', { identifying: true, inverse: 'mainItems' }),
        suggestable: one('Suggestable', { identifying: true, inverse: 'navigableListMainItemViews' }),
    },
});
