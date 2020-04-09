odoo.define('mail.messaging.component.DiscussMobileMailboxSelection', function (require) {
'use strict';

const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;

class DiscussMobileMailboxSelection extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            return {
                allOrderedAndPinnedMailboxes:
                    this.env.entities.Thread.allOrderedAndPinnedMailboxes,
                discussThread: this.env.messaging.discuss.thread,
            };
        }, {
            compareDepth: {
                allOrderedAndPinnedMailboxes: 1,
            },
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging.entity.Discuss}
     */
    get discuss() {
        return this.env.messaging && this.env.messaging.discuss;
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
        const { mailbox } = ev.currentTarget.dataset;
        this.discuss.update({ thread: mailbox });
    }

}

Object.assign(DiscussMobileMailboxSelection, {
    props: {},
    template: 'mail.messaging.component.DiscussMobileMailboxSelection',
});

return DiscussMobileMailboxSelection;

});
