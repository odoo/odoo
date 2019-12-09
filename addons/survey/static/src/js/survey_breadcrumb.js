odoo.define('survey.breadcrumb', function (require) {
'use strict';

var field_utils = require('web.field_utils');
var publicWidget = require('web.public.widget');
var time = require('web.time');
var core = require('web.core');
var _t = core._t;
var QWeb = core.qweb;

publicWidget.registry.SurveyBreadcrumbWidget = publicWidget.Widget.extend({
    xmlDependencies: ['/survey/static/src/xml/survey_templates.xml'],
    events: {
        'click .breadcrumb-item a': '_onBreadcrumbClick',
    },

    /**
     * @override
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.$canGoBack = params.canGoBack;
        this.$currentPageId = params.currentPageId;
        this.$pageIds = params.pageIds;
        this.$pageTitles = params.pageTitles;
    },

    /**
    * @override
    */
    start: function () {
        var superDef = this._super.apply(this, arguments);
        this.updateBreadcrumb(this.$currentPageId);
        return superDef;
    },

    _onBreadcrumbClick: function (event) {
        event.preventDefault();
        var $target = this.$(event.currentTarget).closest('.breadcrumb-item');
        this.$currentPageId = $target.data('pageId');
        this.trigger_up('breadcrumbClick', $target);
    },

    updateBreadcrumb: function (pageId) {
        var $breadcrumb = this.$('.breadcrumb');
        if (pageId) {
            var $breadcrumbTemplate = $(QWeb.render("survey.survey_breadcrumb_template", {
                can_go_back: this.$canGoBack,
                current_page_id: pageId,
                page_ids: this.$pageIds,
                page_titles: this.$pageTitles,
            }));
            this.$el.empty().append($breadcrumbTemplate);
        } else {
            $breadcrumb.addClass('d-none');
        }
    },
});

return publicWidget.registry.SurveyBreadcrumbWidget;

});