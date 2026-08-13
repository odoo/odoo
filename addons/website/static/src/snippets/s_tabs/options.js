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
        new window.Tab($navLink[0]).show();
    },
    /**
     * @override
     */
    _removeItemCallback($target) {
        const $targetNavLink = this.$(`.nav-item a[href="#${$target.attr('id')}"]`);
        const linkIndex = (this.$navLinks.index($targetNavLink) + 1) % this.$navLinks.length;
        const $navLinkToShow = this.$navLinks.eq(linkIndex);
        const $tabPaneToShow = this.$tabPanes.eq(linkIndex);
        $targetNavLink.parent().remove();
        this._findLinksAndPanes();
        $tabPaneToShow[0].classList.add("active", "show");
        new window.Tab($navLinkToShow[0]).show();
    },
});
options.registry.NavTabsStyle = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Manage different tabs styles and their respective classes
     *
     * @see this.selectClass for parameters
     */
    setStyle(previewMode, widgetValue, params) {
        // const $nav = this.$target.find('.s_tabs_nav:first .nav');
        // const isPills = widgetValue === 'pills';
        // $nav.toggleClass('nav-tabs card-header-tabs', !isPills);
        // $nav.toggleClass('nav-pills', isPills);
        // this.$target.find('.s_tabs_nav:first').toggleClass('card-header', !isPills).toggleClass('mb-3', isPills);
        // this.$target.toggleClass('card', !isPills);
        // this.$target.find('.s_tabs_content:first').toggleClass('card-body', !isPills);
        const isTabs = widgetValue === 'nav-tabs';
        const isBtns = widgetValue === 'nav-buttons';

        const mainEl = this.$target[0];
        const tabsEl = this.$target[0].querySelector(".s_tabs_nav");
        const navEl = this.$target[0].querySelector(".s_tabs_nav .nav");
        const contentEl = this.$target[0].querySelector(".s_tabs_content");

        const tabsTabsClasses = ['card-header', 'px-0', 'border-0', 'overflow-x-auto', 'overflow-y-hidden'];
        const navTabsClasses = ['card-header-tabs', 'mx-0', 'px-2', 'border-bottom'];
        const tabsBtnClasses = ['d-flex', 'rounded'];
        const navBtnClasses = ['d-inline-flex', 'nav-pills', 'p-2'];
        const tabsPossibleClasses = params.possibleValues.concat(tabsTabsClasses, tabsBtnClasses);
        const navPossibleClasses = params.possibleValues.concat(navTabsClasses, navBtnClasses);

        // Clean tabsEl from any possible value
        for (const possibleValue of tabsPossibleClasses) {
            possibleValue && tabsEl.classList.remove(possibleValue);
        }

        // Clean navEl from any possible value
        for (const possibleValue of navPossibleClasses) {
            possibleValue && navEl.classList.remove(possibleValue);
        }

        // Apply the new value(s) to tabsEl
        isTabs && tabsEl.classList.add(...tabsTabsClasses);
        isBtns && tabsEl.classList.add(...tabsBtnClasses);

        // Apply the new value(s) to navEl
        widgetValue && navEl.classList.add(widgetValue);
        isTabs && navEl.classList.add(...navTabsClasses);
        isBtns && navEl.classList.add(...navBtnClasses);

        // Adapt other elements accordingly
        mainEl.classList.toggle('card', isTabs);
        tabsEl.classList.toggle('mb-3', !isTabs);
        navEl.classList.toggle('overflow-x-auto', !isTabs);
        navEl.classList.toggle('overflow-y-hidden', !isTabs);
        contentEl.classList.toggle('p-3', isTabs);
    },
    /**
     * Horizontal/vertical nav.
     *
     * @see this.selectClass for parameters
     */
    setDirection: function (previewMode, widgetValue, params) {
        const isVertical = widgetValue === 'vertical';
        const mainEl = this.$target[0];

        // Toggle classes on the main target
        mainEl.classList.toggle('row', isVertical);
        mainEl.classList.toggle('s_col_no_resize', isVertical);
        mainEl.classList.toggle('s_col_no_bgcolor', isVertical);

        // Select relevant elements within mainEl
        const nav = mainEl.querySelector('.s_tabs_nav .nav');
        const navLinks = mainEl.querySelectorAll('.s_tabs_nav .nav .nav-link');
        const tabsNav = mainEl.querySelector('.s_tabs_nav');
        const tabsContent = mainEl.querySelector('.s_tabs_content');

        // Toggle classes based on 'isVertical'
        nav.classList.toggle('flex-sm-column', isVertical);
        navLinks.forEach(link => link.classList.toggle('py-2', isVertical));
        tabsNav.classList.toggle('col-sm-3', isVertical);
        tabsContent.classList.toggle('col-sm-9', isVertical);

        // Clean leftover classes not needed in vertical mode
        isVertical && nav.classList.remove('nav-fill', 'nav-justified', 'justify-content-center', 'justify-content-end');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        const navEl = this.$target[0].querySelector(".s_tabs_nav .nav");

        switch (methodName) {
            case 'setStyle':
                const matchingValue = params.possibleValues.find(value => !navEl || navEl.classList.contains(value));
                return matchingValue;
            case 'setDirection':
                return this.$target.find('.s_tabs_nav:first .nav').hasClass('flex-sm-column') ? 'vertical' : 'horizontal';
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _computeWidgetVisibility(widgetName, params) {
        if (widgetName === "alignment_opt") {
            const isFill = this.$target[0].classList.contains("nav-fill");
            const isJustified = this.$target[0].classList.contains("nav-justified");
            const isVertical = this.$target[0].classList.contains("flex-column");

            return !(isFill || isJustified || isVertical);
        }
        return this._super(...arguments);
    },
});

// Prevent `.nav-items` to be deleted from the bin button
// as it is bypassing the "add(+)/remove(-)" behaviour
options.registry.TabsNavItems = options.Class.extend({
    forceNoDeleteButton: true,
});
