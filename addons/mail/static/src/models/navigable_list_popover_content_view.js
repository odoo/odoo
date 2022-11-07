/** @odoo-module **/

import { one, Model } from '@mail/model';

Model({
    name: 'NavigableListPopoverContentView',
    template: 'mail.NavigableListPopoverContentView',
    fields: {
        navigableListView: one('NavigableListView', { related: 'popoverViewOwner.navigableListViewOwner' }),
        popoverViewOwner: one('PopoverView', { identifying: true, inverse: 'navigableListPopoverContentView' }),
    },
});
