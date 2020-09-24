odoo.define('hr_holidays/static/src/components/thread_view/thread_view.js', function (require) {
'use strict';

const components = {
    ThreadView: require('mail/static/src/components/thread_view/thread_view.js'),
};

const { str_to_datetime } = require('web.time');
const { patch } = require('web.utils');

patch(components.ThreadView, 'hr_holidays/static/src/components/thread_view/thread_view.js', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the "out of office" text for the correspondent of the thread if
     * applicable.
     *
     * @returns {string}
     */
    getOutOfOfficeText() {
        if (!this.threadView.thread.correspondent) {
            return "";
        }
        if (!this.threadView.thread.correspondent.out_of_office_date_end) {
            return "";
        }
        const currentDate = new Date();
        const date = str_to_datetime(this.threadView.thread.correspondent.out_of_office_date_end);
        const options = { day: 'numeric', month: 'short' };
        if (currentDate.getFullYear() !== date.getFullYear()) {
            options.year = 'numeric';
        }
        const formattedDate = date.toLocaleDateString(window.navigator.language, options);
        return _.str.sprintf(this.env._t("Out of office until %s."), formattedDate);
    },

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
