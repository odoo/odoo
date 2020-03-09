odoo.define('website_event.dates', function (require) {
'use strict';

var options = require('web_editor.snippets.options');

options.registry.s_website_event_dates = options.Class.extend({
    selector: ".event_dates",
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        // elements in the options
        this.$startDate = this.$target.find('.o_website_event_date_begin');
        this.$endDate = this.$target.find('.o_website_event_date_end');
        this.$timezone = this.$target.find('*[data-oe-field="date_tz"]');

        this._initValues();

        return this._super.apply(this, arguments);
    },

    _onUserValueUpdate: async function (event) {
        await this._super.apply(this, arguments);

        let attributeName = event.target.getMethodsParams().attributeName;
        let data = this.$target[0].dataset;

        switch (attributeName) {
            case 'startDate': {
                // for visual purpose, update the UI
                this.$target.find('*[data-oe-field="date_begin"]').html(moment.unix(data.startDate).format("LL"));
                // insert the timestamp to save it in the back-end
                this.$startDate.html(data.startDate).addClass('o_dirty');
                break;
            }
            case 'endDate': {
                // for visual purpose, update the UI
                this.$target.find('*[data-oe-field="date_end"]').html(moment.unix(data.endDate).format("LL"));
                // insert the timestamp to save it in the back-end
                this.$endDate.html(data.endDate).addClass('o_dirty');
                break;
            }
            case 'timezone': {
                this.$timezone.html(data.timezone).addClass('o_dirty');
                break;
            }
        }

        // warn the users if the dates are not coherent
        if (data.startDate && data.endDate && parseInt(data.endDate) < parseInt(data.startDate)) {
            this.$el.find('input').addClass('text-danger');
        } else {
            this.$el.find('input.text-danger').removeClass('text-danger');
        }

    },

    /**
     * Set the initial value into the snippet options
     */
    _initValues: function () {
        this.$target[0].dataset['startDate'] = parseInt(this.$startDate.data('timestamp'));
        this.$target[0].dataset['endDate'] = parseInt(this.$endDate.data('timestamp'));
        this.$target[0].dataset['timezone'] = this.$timezone.text();
    },
});
});
