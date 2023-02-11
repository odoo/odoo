odoo.define('survey.print', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var dom = require('web.dom');

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

return publicWidget.registry.SurveyPrintWidget;

});
