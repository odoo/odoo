/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SurveyBreadcrumbWidget = publicWidget.Widget.extend({
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
        this.pages = options.pages;
    },

    // Handlers
    // -------------------------------------------------------------------

    _onBreadcrumbClick: function (event) {
        event.preventDefault();
        this.trigger_up('breadcrumb_click', {
            'previousPageId': this.$(event.currentTarget)
                .closest('.breadcrumb-item')
                .data('pageId')
        });
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

export default publicWidget.registry.SurveyBreadcrumbWidget;
