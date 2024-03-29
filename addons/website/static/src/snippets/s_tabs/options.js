/** @odoo-module **/

import { uniqueId } from "@web/core/utils/functions";
import options from "@web_editor/js/editor/snippets.options";

options.registry.NavTabs = options.registry.MultipleItems.extend({
    isTopOption: true,

    /**
     * @override
     */
    start: function () {
        this._findLinksAndPanes();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    onBuilt: function () {
        this._generateUniqueIDs();
    },
    /**
     * @override
     */
    onClone: function () {
        this._generateUniqueIDs();
    },
    /**
     * @override
     */
    async addItem(previewMode, widgetValue, params) {
        // TODO: In master, change the template instead.
        params.item = ".tab-content:first > .tab-pane.active";
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async removeItem(previewMode, widgetValue, params) {
        // TODO: In master, change the template instead.
        params.item = ".tab-content:first > .tab-pane.active";
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetVisibility: async function (widgetName, params) {
        if (widgetName === 'remove_tab_opt') {
            return (this.$tabPanes.length > 2);
        }
        return this._super(...arguments);
    },
    /**
     * @private
     */
    _findLinksAndPanes: function () {
        this.$navLinks = this.$target.find('.nav:first .nav-link');
        this.$tabPanes = this.$target.find(".tab-content:first > .tab-pane");
    },
    /**
     * @private
     */
    _generateUniqueIDs: function () {
        for (var i = 0; i < this.$navLinks.length; i++) {
            var id = uniqueId(new Date().getTime() + "_");
            var idLink = 'nav_tabs_link_' + id;
            var idContent = 'nav_tabs_content_' + id;
            this.$navLinks.eq(i).attr({
                'id': idLink,
                'href': '#' + idContent,
                'aria-controls': idContent,
            });
            this.$tabPanes.eq(i).attr({
                'id': idContent,
                'aria-labelledby': idLink,
            });
        }
    },
    /**
     * @override
     */
    _addItemCallback($target) {
        $target.removeClass('active show');
        const $targetNavItem = this.$(`.nav-item a[href="#${$target.attr('id')}"]`)
            .removeClass('active show').parent();
        const $navLink = $targetNavItem.clone().insertAfter($targetNavItem)
            .find('.nav-link');
        this._findLinksAndPanes();
        this._generateUniqueIDs();
        $navLink.tab('show');
    },
    /**
     * @override
     */
    _removeItemCallback($target) {
        const $targetNavLink = this.$(`.nav-item a[href="#${$target.attr('id')}"]`);
        const $navLinkToShow = this.$navLinks.eq((this.$navLinks.index($targetNavLink) + 1) % this.$navLinks.length);
        $targetNavLink.parent().remove();
        this._findLinksAndPanes();
        $navLinkToShow.tab('show');
    },
});
options.registry.NavTabsStyle = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Set the style of the tabs.
     *
     * @see this.selectClass for parameters
     */
    setStyle: function (previewMode, widgetValue, params) {
        const $nav = this.$target.find('.s_tabs_nav:first .nav');
        const isPills = widgetValue === 'pills';
        $nav.toggleClass('nav-tabs card-header-tabs', !isPills);
        $nav.toggleClass('nav-pills', isPills);
        this.$target.find('.s_tabs_nav:first').toggleClass('card-header', !isPills).toggleClass('mb-3', isPills);
        this.$target.toggleClass('card', !isPills);
        this.$target.find('.s_tabs_content:first').toggleClass('card-body', !isPills);
    },
    /**
     * Horizontal/vertical nav.
     *
     * @see this.selectClass for parameters
     */
    setDirection: function (previewMode, widgetValue, params) {
        const isVertical = widgetValue === 'vertical';
        this.$target.toggleClass('row s_col_no_resize s_col_no_bgcolor', isVertical);
        this.$target.find('.s_tabs_nav:first .nav').toggleClass('flex-column', isVertical);
        this.$target.find('.s_tabs_nav:first > .nav-link').toggleClass('py-2', isVertical);
        this.$target.find('.s_tabs_nav:first').toggleClass('col-md-3', isVertical);
        this.$target.find('.s_tabs_content:first').toggleClass('col-md-9', isVertical);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'setStyle':
                return this.$target.find('.s_tabs_nav:first .nav').hasClass('nav-pills') ? 'pills' : 'tabs';
            case 'setDirection':
                return this.$target.find('.s_tabs_nav:first .nav').hasClass('flex-column') ? 'vertical' : 'horizontal';
        }
        return this._super(...arguments);
    },
});
