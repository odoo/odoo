odoo.define('hr_holidays/static/src/components/thread_viewer/thread_viewer.js', function (require) {
'use strict';

const components = {
    ThreadViewer: require('mail/static/src/components/thread_viewer/thread_viewer.js'),
};

const { str_to_datetime } = require('web.time');
const { patch } = require('web.utils');

patch(components.ThreadViewer, 'hr_holidays/static/src/components/thread_viewer/thread_viewer.js', {

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
        if (!this.threadViewer.thread.correspondent) {
            return "";
        }
        if (!this.threadViewer.thread.correspondent.out_of_office_date_end) {
            return "";
        }
        const currentDate = new Date();
        const date = str_to_datetime(this.threadViewer.thread.correspondent.out_of_office_date_end);
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
        const threadViewer = this.env.models['mail.thread_viewer'].get(props.threadViewerLocalId);
        const thread = threadViewer ? threadViewer.thread : undefined;
        const correspondent = thread ? thread.correspondent : undefined;
        return Object.assign({}, res, {
            correspondent: correspondent ? correspondent.__state : undefined,
        });
    },
});

});
