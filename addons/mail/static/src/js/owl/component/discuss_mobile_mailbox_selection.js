odoo.define('mail.component.DiscussMobileMailboxSelection', function () {
'use strict';

class MobileMailboxSelection extends owl.Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeGetters = owl.hooks.useGetters();
        this.storeProps = owl.hooks.useStore(() => {
            return {
                pinnedMailboxList: this.storeGetters.pinnedMailboxList(),
            };
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        this.trigger('o-select-thread', {
            threadLocalId: ev.currentTarget.dataset.mailboxLocalId,
        });
    }
}

MobileMailboxSelection.props = {
    activeThreadLocalId: {
        type: String,
        optional: true,
    },
};

MobileMailboxSelection.template = 'mail.component.DiscussMobileMailboxSelection';

return MobileMailboxSelection;

});
