/** @odoo-module **/

import { many, one, registerModel } from '@mail/model';

registerModel({
    name: 'DiscussMobileMailboxSelectionView',
    template: 'mail.DiscussMobileMailboxSelectionView',
    fields: {
        items: many('DiscussMobileMailboxSelectionItemView', { inverse: 'owner',
            compute() {
                return this.owner.orderedMailboxes.map(mailbox => ({ mailbox }));
            },
        }),
        owner: one('DiscussView', { identifying: true, inverse: 'mobileMailboxSelectionView' }),
    },
});
