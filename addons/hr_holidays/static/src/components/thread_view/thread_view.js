odoo.define('hr_holidays/static/src/components/thread_view/thread_view.js', function (require) {
'use strict';

const components = {
    ThreadView: require('mail/static/src/components/thread_view/thread_view.js'),
};

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
        if (!this.threadView.__mfield_thread(this).__mfield_correspondent(this)) {
            return "";
        }
        if (!this.threadView.__mfield_thread(this).__mfield_correspondent(this).__mfield_out_of_office_date_end(this)) {
            return "";
        }
        const currentDate = new Date();
        const date = this.threadView.__mfield_thread(this).__mfield_correspondent(this).__mfield_out_of_office_date_end(this);
        const options = { day: 'numeric', month: 'short' };
        if (currentDate.getFullYear() !== date.getFullYear()) {
            options.year = 'numeric';
        }
        const formattedDate = date.toLocaleDateString(window.navigator.language, options);
        return _.str.sprintf(this.env._t("Out of office until %s."), formattedDate);
    },

});

});
