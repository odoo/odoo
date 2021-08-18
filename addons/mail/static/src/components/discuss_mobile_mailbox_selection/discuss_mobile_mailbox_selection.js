/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class DiscussMobileMailboxSelection extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread[]}
     */
    get orderedMailboxes() {
        if (!this.messaging) {
            return [];
        }
        return this.messaging.models['mail.thread']
            .all(thread => thread.isPinned && thread.model === 'mail.box')
            .sort((mailbox1, mailbox2) => {
                if (mailbox1 === this.messaging.inbox) {
                    return -1;
                }
                if (mailbox2 === this.messaging.inbox) {
                    return 1;
                }
                if (mailbox1 === this.messaging.starred) {
                    return -1;
                }
                if (mailbox2 === this.messaging.starred) {
                    return 1;
                }
                const mailbox1Name = mailbox1.displayName;
                const mailbox2Name = mailbox2.displayName;
                mailbox1Name < mailbox2Name ? -1 : 1;
            });
    }

    /**
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.messaging && this.messaging.discuss;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when clicking on a mailbox selection item.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        const { mailboxLocalId } = ev.currentTarget.dataset;
        const mailbox = this.messaging.models['mail.thread'].get(mailboxLocalId);
        if (!mailbox) {
            return;
        }
        mailbox.open();
    }

}

Object.assign(DiscussMobileMailboxSelection, {
    props: {},
    template: 'mail.DiscussMobileMailboxSelection',
});

registerMessagingComponent(DiscussMobileMailboxSelection);
