odoo.define('mail.component.ThreadIcon', function () {
'use strict';

class ThreadIcon extends owl.Component {

    /**
     * @override
     * @param {...any} args
     */
    constructor(...args) {
        super(...args);
        this.storeProps = owl.hooks.useStore((state, props) => {
            const thread = state.threads[props.threadLocalId];
            const directPartner = thread
                ? state.partners[thread.directPartnerLocalId]
                : undefined;
            return {
                directPartner,
                thread,
            };
        });
    }
}

ThreadIcon.props = {
    threadLocalId: String,
};

ThreadIcon.template = 'mail.component.ThreadIcon';

return ThreadIcon;

});
