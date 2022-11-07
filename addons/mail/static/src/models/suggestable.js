/** @odoo-module **/

import { many, one, Model } from '@mail/model';

Model({
    name: 'Suggestable',
    identifyingMode: 'xor',
    fields: {
        cannedResponse: one('CannedResponse', { identifying: true, inverse: 'suggestable' }),
        channelCommand: one('ChannelCommand', { identifying: true, inverse: 'suggestable' }),
        navigableListExtraItemViews: many('NavigableListExtraItemView', { inverse: 'suggestable' }),
        navigableListMainItemViews: many('NavigableListMainItemView', { inverse: 'suggestable' }),
        partner: one('Partner', { identifying: true, inverse: 'suggestable' }),
        thread: one('Thread', { identifying: true, inverse: 'suggestable' }),
    },
});
