odoo.define('hr_holidays/static/src/components/thread_view/thread_view.js', function (require) {
'use strict';

const components = {
    ThreadView: require('mail/static/src/components/thread_view/thread_view.js'),
};

const { patch } = require('web.utils');

patch(components.ThreadView, 'hr_holidays/static/src/components/thread_view/thread_view.js', {
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _useStoreSelector(props) {
        const res = this._super(...arguments);
        const threadView = this.env.models['mail.thread_view'].get(props.threadViewLocalId);
        const thread = threadView ? threadView.thread : undefined;
        const correspondent = thread ? thread.correspondent : undefined;
        return Object.assign({}, res, {
            correspondent: correspondent ? correspondent.__state : undefined,
        });
    },
});

});
