/** @odoo-module **/

import { one, registerModel } from '@mail/model';

registerModel({
    name: 'DiscussMobileMailboxSelectionItemView',
    template: 'mail.DiscussMobileMailboxSelectionItemView',
    recordMethods: {
        onClick() {
            if (!this.exists()) {
                return;
            }
            this.mailbox.thread.open();
        },
    },
    fields: {
        mailbox: one('Mailbox', { identifying: true, inverse: 'discussMobileSelectionItems' }),
        owner: one('DiscussMobileMailboxSelectionView', { identifying: true, inverse: 'items' }),
    },
});
