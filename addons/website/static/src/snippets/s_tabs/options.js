odoo.define('website.s_tabs_options', function (require) {
'use strict';

const snippetOptions = require('web_editor.snippets.options');

snippetOptions.registry.NavTabs = snippetOptions.SnippetOptionWidget.extend({
    isTopOption: true,

    /**
     * @override
     */
    start: async function () {
        this._findLinksAndPanes();
        await this._super.apply(this, arguments);
        await this._refreshTarget();
    },
    /**
     * @override
     */
    onBuilt: async function () {
        this._generateUniqueIDs();
        await this._refreshTarget();
    },
    /**
     * @override
     */
    onClone: async function () {
        this._generateUniqueIDs();
        this._refreshTarget();
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Creates a new tab and tab-pane.
     *
     * @see this.selectClass for parameters
     */
    addTab: async function (previewMode, widgetValue, params) {
        this._findLinksAndPanes();
        var $activeItem = this.$navLinks.filter('.active').parent();
        var $activePane = this.$tabPanes.filter('.active');

        var $navItem = $activeItem.clone();
        var $navLink = $navItem.find('.nav-link').removeClass('active show');
        var $tabPane = $activePane.clone().removeClass('active show');
        $navItem.insertAfter($activeItem);
        $tabPane.insertAfter($activePane);

        if (previewMode === false) await this._refreshTarget();

        this._generateUniqueIDs();

        $navLink.tab('show');

    },
    /**
     * Removes the current active tab and its content.
     *
     * @see this.selectClass for parameters
     */
    removeTab: async function (previewMode, widgetValue, params) {
        this._findLinksAndPanes();
        var self = this;

        var $activeLink = this.$navLinks.filter('.active');
        var $activePane = this.$tabPanes.filter('.active');

        var $next = this.$navLinks.eq((this.$navLinks.index($activeLink) + 1) % this.$navLinks.length);

        await new Promise(resolve => {
            $next.one('shown.bs.tab', function () {
                $activeLink.parent().remove();
                $activePane.remove();
                self._findLinksAndPanes();
                resolve();
            });
            $next.tab('show');
        });

        if (previewMode === false) await this._refreshTarget();
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
        this.$tabPanes = this.$target.find('.tab-content:first .tab-pane');
    },
    /**
     * @private
     */
    _generateUniqueIDs: function () {
        this._findLinksAndPanes();
        for (var i = 0; i < this.$navLinks.length; i++) {
            var id = _.now() + '_' + _.uniqueId();
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
});
snippetOptions.registry.NavTabsStyle = snippetOptions.SnippetOptionWidget.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Set the style of the tabs.
     *
     * @see this.selectClass for parameters
     */
    setStyle: async function (previewMode, widgetValue, params) {
        const $nav = this.$target.find('.s_tabs_nav:first .nav');
        const isPills = widgetValue === 'pills';
        $nav.toggleClass('nav-tabs card-header-tabs', !isPills);
        $nav.toggleClass('nav-pills', isPills);
        this.$target.find('.s_tabs_nav:first').toggleClass('card-header', !isPills).toggleClass('mb-3', isPills);
        this.$target.toggleClass('card', !isPills);
        this.$target.find('.s_tabs_content:first').toggleClass('card-body', !isPills);

        if (previewMode === false) await this._refreshTarget();
    },
    /**
     * Horizontal/vertical nav.
     *
     * @see this.selectClass for parameters
     */
    setDirection: async function (previewMode, widgetValue, params) {
        const isVertical = widgetValue === 'vertical';
        this.$target.toggleClass('row s_col_no_resize s_col_no_bgcolor', isVertical);
        this.$target.find('.s_tabs_nav:first .nav').toggleClass('flex-column', isVertical);
        this.$target.find('.s_tabs_nav:first > .nav-link').toggleClass('py-2', isVertical);
        this.$target.find('.s_tabs_nav:first').toggleClass('col-md-3', isVertical);
        this.$target.find('.s_tabs_content:first').toggleClass('col-md-9', isVertical);

        if (previewMode === false) await this._refreshTarget();
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
});
