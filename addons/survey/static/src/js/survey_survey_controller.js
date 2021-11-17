odoo.define('survey.SurveyFormController', function (require) {
'use strict';

const FormController = require('web.FormController');
const core = require('web.core');

const _t = core._t;


return FormController.extend({
    custom_events: _.extend({}, FormController.prototype.custom_events, {
        save_form_before_new_question: '_saveFormBeforeNewQuestion',
    }),

    _saveFormBeforeNewQuestion: async function (ev) {
        if (ev) {
            ev.stopPropagation();
        }
        // Run this pipeline synchronously before opening editor form to update/create
        return await this.saveRecord(null, {
            stayInEdit: true,
            reload: true,
        }).then(function () {
            if (ev && ev.data.callback)
                ev.data.callback();
            return Promise.resolve("Survey saved")
        }).catch(reason => {
            return Promise.reject(reason);
        })
    }
});

});