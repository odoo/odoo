odoo.define('mail.component.ChatterTopbar', function (require) {
'use strict';

const { Component } = owl;
const { useStore } = owl.hooks;

class ChatterTopbar extends Component {
    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeProps = useStore((state, props) => {
            const thread = state.threads[props.threadLocalId];
            return {
                attachmentsAmount: thread && thread.attachmentLocalIds
                    ? thread.attachmentLocalIds.length
                    : 0,
                followersAmount: 0
            };
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickAttachments(ev) {
        this.trigger('o-chatter-topbar-select-attachment');
    }
}

ChatterTopbar.props = {
    threadLocalId: String,
};

ChatterTopbar.template = 'mail.component.ChatterTopbar';

return ChatterTopbar;

});
