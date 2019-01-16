odoo.define('survey.form.widget', function(require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var Widget = require('web.Widget');

var qweb = core.qweb;

var SurveyFormWidget = Widget.extend({
    template: false,
    events: {
    },


    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.options = _.defaults(options || {}, {
        });
        console.log(this.options);
    },

    /**
     * @override
     */
    // willStart: function () {
    //     // init data
    //     // load qweb template
    //     return this._loadTemplates();
    // },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {Deferred}
     */
    // _loadTemplates: function () {
    //     return ajax.loadXML('/survey/static/src/xml/survey_prefill_widget.xml', qweb);
    // },
});

return SurveyFormWidget;

});