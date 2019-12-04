odoo.define('survey.breadcrumb', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');
var QWeb = core.qweb;

publicWidget.registry.SurveyBreadcrumbWidget = publicWidget.Widget.extend({
    xmlDependencies: ['/survey/static/src/xml/survey_templates.xml'],
    template: "survey.survey_breadcrumb_template",
    events: {
        'click .breadcrumb-item a': '_onBreadcrumbClick',
    },

    /**
     * @override
     */
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.canGoBack = options.canGoBack;
        this.currentPageId = options.currentPageId;
        this.pageIds = options.pageIds;
        this.pageTitles = options.pageTitles;
    },

    // Handlers
    // -------------------------------------------------------------------

    _onBreadcrumbClick: function (event) {
        event.preventDefault();
        this.trigger_up('breadcrumb_click', this.$(event.currentTarget).closest('.breadcrumb-item'));
    },

    // PUBLIC METHODS
    // -------------------------------------------------------------------

    updateBreadcrumb: function (pageId) {
        if (pageId) {
            this.currentPageId = pageId;
            this.renderElement();
        } else {
            this.$('.breadcrumb').addClass('d-none');
        }
    },
});

return publicWidget.registry.SurveyBreadcrumbWidget;

});
