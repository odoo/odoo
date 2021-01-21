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
        const thread = res.thread;
        const correspondent = thread && thread.correspondent;
        return Object.assign({}, res, {
            correspondentOutOfOfficeText: correspondent && correspondent.outOfOfficeText,
        });
    },
});

});
