/** @odoo-module **/

import { one, Model } from '@mail/model';

Model({
    name: 'NavigableListMainOrExtraItemView',
    template: 'mail.NavigableListMainOrExtraItemView',
    identifyingMode: 'xor',
    fields: {
        extraItemViewOwner: one('NavigableListExtraItemView',{ identifying: true, inverse: 'navigableListMainOrExtraItemView' }),
        itemView: one('NavigableListItemView', { default:{}, inverse: 'navigableListMainOrExtraItemView' }),
        mainItemViewOwner: one('NavigableListMainItemView', { identifying: true, inverse: 'navigableListMainOrExtraItemView' }),
        navigableListView: one('NavigableListView', {
            compute() {
                if (this.extraItemViewOwner) {
                    return this.extraItemViewOwner.navigableListViewOwner;
                }
                if (this.mainItemViewOwner) {
                    return this.mainItemViewOwner.navigableListViewOwner;
                }
                return clear();
            }
        }),
    },
});
