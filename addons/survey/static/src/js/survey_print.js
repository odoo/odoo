/** @odoo-module alias=survey.print **/

import publicWidget from "web.public.widget";
import dom from "web.dom";

publicWidget.registry.SurveyPrintWidget = publicWidget.Widget.extend({
    selector: '.o_survey_print',

    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
    * @override
    */
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            // Will allow the textarea to resize if any carriage return instead of showing scrollbar.
            self.$('textarea').each(function () {
                dom.autoresize($(this));
            });
        });
    },

});

export default publicWidget.registry.SurveyPrintWidget;
