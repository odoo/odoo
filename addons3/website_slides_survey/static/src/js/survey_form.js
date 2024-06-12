/** @odoo-module **/

import { ShareMail } from '@website_slides/js/slides_share';
import SurveyFormWidget from '@survey/js/survey_form';

SurveyFormWidget.include({
    _onNextScreenDone(options) {
        this._super(...arguments);

        new ShareMail(this).attachTo($('.oe_slide_js_share_email'));
    }
});
