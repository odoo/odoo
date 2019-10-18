odoo.define('web.ControlPanelRenderer', function (require) {
"use strict";

var config = require('web.config');
var data = require('web.data');
var FavoriteMenu = require('web.FavoriteMenu');
var FilterMenu = require('web.FilterMenu');
var GroupByMenu = require('web.GroupByMenu');
var mvc = require('web.mvc');
var SearchBar = require('web.SearchBar');
var TimeRangeMenu = require('web.TimeRangeMenu');

var Renderer = mvc.Renderer;

var ControlPanelRenderer = Renderer.extend({
    template: 'ControlPanel',
    custom_events: {
        get_action_info: '_onGetActionInfo',
    },
    events: _.extend({}, Renderer.prototype.events, {
        'click .o_searchview_more': '_onMore',
    }),

    /**
     * @override
     * @param {Object} [params.action] current action if any
     * @param {Object} [params.context]
     * @param {Object[]} [params.breadcrumbs=[]] list of breadcrumbs elements
     * @param {boolean} [params.withBreadcrumbs=false] if false, breadcrumbs
     *   won't be rendered
     * @param {boolean} [params.withSearchBar=false] if false, no search bar
     *   is rendered
     * @param {string[]} [params.searchMenuTypes=[]] determines the search menus
     *   that are displayed.
     * @param {String} [params.template] the QWeb template to render the
     *   ControlPanel. By default, the template 'ControlPanel' will be used.
     * @param {string} [params.title=''] the title visible in control panel
     */
    init: function (parent, state, params) {
        this._super.apply(this, arguments);
        this._breadcrumbs = params.breadcrumbs || [];
        this._title = params.title || '';
        this.withBreadcrumbs = params.withBreadcrumbs;
        this.withSearchBar = params.withSearchBar;
        if (params.template) {
            this.template = params.template;
        }
        this.context = params.context;

        this.$subMenus = null;
        this.action = params.action;
        this.displaySearchMenu = true;
        this.isMobile = config.device.isMobile;
        this.menusSetup = false;
        this.searchMenuTypes = params.searchMenuTypes || [];
        this.subMenus = {};
    },
    /**
     * Render the control panel and create a dictionnary of its exposed elements.
     *
     * @override
     */
    start: function () {
        var self = this;

        // exposed jQuery nodesets
        this.nodes = {
            $buttons: this.$('.o_cp_buttons'),
            $pager: this.$('.o_cp_pager'),
            $sidebar: this.$('.o_cp_sidebar'),
            $switch_buttons: this.$('.o_cp_switch_buttons'),
        };

        // if we don't use the default search bar and buttons, we expose the
        // corresponding areas for custom content
        if (!this.withSearchBar) {
            this.nodes.$searchview = this.$('.o_cp_searchview');
        }
        if (this.searchMenuTypes.length === 0) {
            this.nodes.$searchview_buttons = this.$('.o_search_options');
        }

        if (this.withBreadcrumbs) {
            this._renderBreadcrumbs();
        }

        var superDef = this._super.apply(this, arguments);
        var searchDef = this._renderSearch();
        return Promise.all([superDef, searchDef]).then(function () {
            self._setSearchMenusVisibility();
        });
    },
    /**
     * @override
     */
    on_attach_callback: function () {
        this._focusSearchInput();
    },
    /**
     * @override
     */
    on_detach_callback: function () {
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Object|undefined}
     */
    getLastFacet: function () {
        return this.state.facets.slice(-1)[0];
    },
    /**
     * This function is called when actions call 'updateControlPanel' with
     * custom contents to insert in the exposed areas.
     *
     * @param {Object} status
     * @param {Object} [status.cp_content] dictionnary containing the jQuery
     *   elements to insert in the exposed areas
     * @param {string} [status.breadcrumbs] the breadcrumbs to display before
     *   the current controller
     * @param {string} [status.title] the title of the current controller, to
     *   display at the end of the breadcrumbs
     * @param {Object} [options]
     * @param {Boolean} [options.clear=true] set to false to keep control panel
     *   elements that are not in status.cp_content (useful for partial updates)
     */
    updateContents: function (status, options) {
        var new_cp_content = status.cp_content || {};
        var clear = 'clear' in (options || {}) ? options.clear : true;

        if (this.withBreadcrumbs) {
            this._breadcrumbs = status.breadcrumbs || this._breadcrumbs;
            this._title = status.title || this._title;
            this._renderBreadcrumbs();
        }

        if (clear) {
            this._detachContent(this.nodes);
        } else {
            this._detachContent(_.pick(this.nodes, _.keys(new_cp_content)));
        }
        this._attachContent(new_cp_content);
    },
    /**
     * Update the state of the renderer state. It retriggers a full rerendering.
     *
     * @param {Object} state
     * @returns {Promise}
     */
    updateState: function (state) {
        this.state = state;
        return this._renderSearch();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} content dictionnary of jQuery elements to attach, whose
     *   keys are jQuery nodes identifiers in this.nodes
     */
    _attachContent: function (content) {
        for (var $element in content) {
            var $nodeset = content[$element];
            if ($nodeset && this.nodes[$element]) {
                this.nodes[$element].append($nodeset);
            }
        }
    },
    /**
     * @private
     * @param {Object} content subset of this.nodes to detach
     */
    _detachContent: function (content) {
        for (var $element in content) {
            content[$element].contents().detach();
        }
    },
    /**
     * @private
     */
    _focusSearchInput: function () {
        if (this.withSearchBar && !config.device.isMobile) {
            // in mobile mode, we would rather not focus manually the
            // input, because it opens up the integrated keyboard, which is
            // not what you expect when you just selected a filter.
            this.searchBar.focus();
        }
    },
    /**
     * @private
     * @param {string} menuType
     * @returns {Objects[]} menuItems
     */
    _getMenuItems: function (menuType) {
        var menuItems;
        if (menuType === 'filter') {
            menuItems = this.state.filters;
        }
        if (menuType === 'groupBy') {
            menuItems = this.state.groupBys;
        }
        if (menuType === 'timeRange') {
            menuItems = this.state.timeRanges;
        }
        if (menuType === 'favorite') {
            menuItems = this.state.favorites;
        }
        return menuItems;
    },
    /**
     * @private
     * @returns {jQueryElement}
     */
    _getSubMenusPlace: function () {
        return $('<div>').appendTo(this.$('.o_search_options'));
    },
    /**
     * @private
     */
    _renderBreadcrumbs: function () {
        var self = this;
        var breadcrumbsDescriptors = this._breadcrumbs.concat({title: this._title});
        var breadcrumbs = breadcrumbsDescriptors.map(function (bc, index) {
            return self._renderBreadcrumbsItem(bc, index, breadcrumbsDescriptors.length);
        });
        this.$('.breadcrumb').html(breadcrumbs);
    },
    /**
     * Render a breadcrumbs' li jQuery element.
     *
     * @private
     * @param {Object} bc
     * @param {string} bc.title
     * @param {string} bc.controllerID
     * @param {integer} index
     * @param {integer} length
     * @returns {jQueryElement} $bc
     */
    _renderBreadcrumbsItem: function (bc, index, length) {
        var self = this;
        var is_last = (index === length-1);
        var li_content = bc.title && _.escape(bc.title.trim()) || data.noDisplayContent;
        var $bc = $('<li>', {class: 'breadcrumb-item'})
            .append(is_last ? li_content : $('<a>', {href: '#'}).html(li_content))
            .toggleClass('active', is_last);
        if (!is_last) {
            $bc.click(function (ev) {
                ev.preventDefault();
                self.trigger_up('breadcrumb_clicked', {controllerID: bc.controllerID});
            });
        }

        var secondLast = index === length - 2;
        if (secondLast) {
            $bc.attr('accessKey', 'b');
        }

        return $bc;
    },
    /**
     * Renderer the search bar and the search menus
     *
     * @private
     * @returns {Promise}
     */
    _renderSearch: function () {
        var defs = [];
        if (this.menusSetup) {
            this._updateMenus();
        } else {
            this.menusSetup = true;
            defs = defs.concat(this._setupMenus());
        }
        if (this.withSearchBar) {
            defs.push(this._renderSearchBar());
        }
        return Promise.all(defs).then(this._focusSearchInput.bind(this));
    },
    /**
     * @private
     * @returns {Promise}
     */
    _renderSearchBar: function () {
        // TODO: might need a reload instead of a destroy/instantiate
        var oldSearchBar = this.searchBar;
        this.searchBar = new SearchBar(this, {
            context: this.context,
            facets: this.state.facets,
            fields: this.state.fields,
            filterFields: this.state.filterFields,
        });
        return this.searchBar.appendTo(this.$('.o_searchview')).then(function () {
            if (oldSearchBar) {
                oldSearchBar.destroy();
            }
        });
    },
    /**
     * Hide or show the search menus according to this.displaySearchMenu.
     *
     * @private
     */
    _setSearchMenusVisibility: function () {
        this.$('.o_searchview_more')
            .toggleClass('fa-search-plus', !this.displaySearchMenu)
            .toggleClass('fa-search-minus', this.displaySearchMenu);
        this.$('.o_search_options')
            .toggleClass('o_hidden', !this.displaySearchMenu);
    },
    /**
     * Create a new menu of the given type and append it to this.$subMenus.
     * This menu is also added to this.subMenus.
     *
     * @private
     * @param {string} menuType
     * @returns {Promise}
     */
    _setupMenu: function (menuType) {
        var Menu;
        var menu;
        if (menuType === 'filter') {
            Menu = FilterMenu;
        }
        if (menuType === 'groupBy') {
            Menu = GroupByMenu;
        }
        if (menuType === 'timeRange') {
            Menu = TimeRangeMenu;
        }
        if (menuType === 'favorite') {
            Menu = FavoriteMenu;
        }
        if (_.contains(['filter', 'groupBy', 'timeRange'], menuType)) {
            menu = new Menu(this, this._getMenuItems(menuType), this.state.fields);
        }
        if (menuType === 'favorite') {
            menu = new Menu(this, this._getMenuItems(menuType), this.action);
        }
        this.subMenus[menuType] = menu;
        return menu.appendTo(this.$subMenus);
    },
    /**
     * Instantiate the search menu determined by this.searchMenuTypes.
     *
     * @private
     * @returns {Promise[]}
     */
    _setupMenus: function () {
        this.$subMenus = this._getSubMenusPlace();
        return this.searchMenuTypes.map(this._setupMenu.bind(this));
    },
    /**
     * Update the search menus.
     *
     * @private
     */
    _updateMenus: function () {
        var self = this;
        this.searchMenuTypes.forEach(function (menuType) {
            self.subMenus[menuType].update(self._getMenuItems(menuType));
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Toggle the search menus visibility.
     *
     * @private
     */
    _onMore: function () {
        this.displaySearchMenu = !this.displaySearchMenu;
        this._setSearchMenusVisibility();
    },
});

return ControlPanelRenderer;

});
