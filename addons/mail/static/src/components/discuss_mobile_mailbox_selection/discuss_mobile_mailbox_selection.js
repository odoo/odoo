odoo.define('mail/static/src/components/discuss_mobile_mailbox_selection/discuss_mobile_mailbox_selection.js', function (require) {
'use strict';

const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;

class DiscussMobileMailboxSelection extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.thread[]}
     */
    get orderedMailboxes() {
        return this.env.models['mail.thread']
            .all(thread =>
                thread.__mfield_isPinned(this) &&
                thread.__mfield_model(this) === 'mail.box'
            )
            .sort((mailbox1, mailbox2) => {
                if (mailbox1 === this.env.messaging.__mfield_inbox(this)) {
                    return -1;
                }
                if (mailbox2 === this.env.messaging.__mfield_inbox(this)) {
                    return 1;
                }
                if (mailbox1 === this.env.messaging.__mfield_starred(this)) {
                    return -1;
                }
                if (mailbox2 === this.env.messaging.__mfield_starred(this)) {
                    return 1;
                }
                const mailbox1Name = mailbox1.__mfield_displayName(this);
                const mailbox2Name = mailbox2.__mfield_displayName(this);
                mailbox1Name < mailbox2Name ? -1 : 1;
            });
    }

    /**
     * @returns {mail.discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.__mfield_discuss(this);
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
        const mailbox = this.env.models['mail.thread'].get(mailboxLocalId);
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

return DiscussMobileMailboxSelection;

});
