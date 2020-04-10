odoo.define('hr_holidays.messaging.component.ThreadViewer', function (require) {
'use strict';

const components = {
    ThreadViewer: require('mail.messaging.component.ThreadViewer'),
};

const { str_to_datetime } = require('web.time');
const { patch } = require('web.utils');

patch(components.ThreadViewer, 'hr_holidays.messaging.component.ThreadViewer', {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Returns the "out of office" text for the direct partner of the thread if
     * applicable.
     *
     * @returns {string}
     */
    getOutOfOfficeText() {
        if (!this.threadViewer.thread.directPartner) {
            return "";
        }
        if (!this.threadViewer.thread.directPartner.out_of_office_date_end) {
            return "";
        }
        const currentDate = new Date();
        const date = str_to_datetime(this.threadViewer.thread.directPartner.out_of_office_date_end);
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
        const directPartner = res.thread ? res.thread.directPartner : undefined;
        return Object.assign({}, res, {
            directPartner,
        });
    },
});

});
