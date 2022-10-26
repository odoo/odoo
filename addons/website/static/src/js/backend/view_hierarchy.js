odoo.define('website.view_hierarchy', function (require) {
"use strict";

const core = require('web.core');
const qweb = require('web.qweb');
const viewRegistry = require('web.view_registry');

const _t = core._t;

const Renderer = qweb.Renderer.extend({
    events: _.extend({}, qweb.Renderer.prototype.events, {
        'click .js_fold': '_onCollapseClick',
        'click .o_website_filter a': '_onWebsiteFilterClick',
        'click .o_search button': '_onSearchButtonClick',
        'click .o_show_diff': '_onShowDiffClick',
        'click .o_load_hierarchy': '_onLoadHierarchyClick',
        'keydown .o_search input': '_onSearchInputKeyDown',
        'input .o_search input': '_onSearchInputKeyInput',
        'change #o_show_inactive': '_onShowActiveClick',
    }),
    /**
     * @override
     */
    init: function () {
        this._super(...arguments);

        // Search
        this.cptFound = 0;
        this.prevSearch = '';
    },
    /**
     * @override
     */
    on_attach_callback: function () {
        this._super(...arguments);

        const self = this;
        this._handleLastVisibleChild();
        // Fixed Navbar
        this.$('.o_tree_container').css({
            'padding-top': this.$('.o_tree_nav').outerHeight() + 10,
        });
        // Website Filters
        this.$wNodes = this.$("li[data-website_name]");
        this.$notwNodes = this.$("li:not([data-website_name])");
        const websiteNames = _.uniq($.map(self.$wNodes, el => el.getAttribute('data-website_name')));
        for (const websiteName of websiteNames) {
            this.$('.o_website_filter').append($('<a/>', {
                'class': 'dropdown-item',
                'data-website_name': websiteName,
                'text': websiteName,
            }));
        }
        this.$(`.o_website_filter a[data-website_name="${websiteNames[0] || '*'}"]`).click();
        // Highlight requested view as google does
        const reqViewId = this.$('.o_tree_container').data('requested-view-id');
        const $reqView = $(`[data-id="${reqViewId}"] span.js_fold`).first();
        $reqView.css({'background-color': 'yellow'});
        $('.o_content').scrollTo($reqView[0], 300, {offset: -200});
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onCollapseClick: function (ev) {
        const $parent = $(ev.currentTarget).parent();
        const folded = $parent.find('.o_fold_icon').hasClass('fa-plus-square-o');
        let $ul, $oFoldIcon;
        if (folded) { // Unfold only self
            $ul = $parent.siblings('ul');
            $oFoldIcon = $parent.find('.o_fold_icon');
        } else { // Fold all
            $ul = $parent.parent().find('ul');
            $oFoldIcon = $parent.parent().find('.o_fold_icon');
        }
        $ul.toggleClass('d-none', !folded);
        $oFoldIcon.toggleClass('fa-minus-square-o', folded).toggleClass('fa-plus-square-o', !folded);
        this._handleLastVisibleChild();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onShowActiveClick: function (ev) {
        this.$('.o_is_inactive').toggleClass('d-none', !ev.currentTarget.checked);
        this._handleLastVisibleChild();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onWebsiteFilterClick: function (ev) {
        ev.preventDefault();
        // Update Dropdown Filter
        const $el = $(ev.currentTarget);
        $el.addClass('active').siblings().removeClass('active');
        $el.parent().siblings('.dropdown-toggle').text($el.text());
        // Show all views
        const websiteName = $el.data('website_name');
        this.$wNodes.add(this.$notwNodes).removeClass('d-none');
        if (websiteName !== '*') {
            // Hide all website views
            this.$wNodes.addClass('d-none');
            // Show selected website views
            const $selectedWebsiteNodes = this.$(`li[data-website_name="${websiteName}"]`);
            $selectedWebsiteNodes.removeClass('d-none');
            // Hide generic siblings
            $selectedWebsiteNodes.each(function () {
                $(this).siblings(`li[data-key="${$(this).data('key')}"]:not([data-website_name])`).addClass('d-none');
            });
        }
        // Preserve current inactive toggle state
        this.$('.o_is_inactive').toggleClass('d-none', !$('#o_show_inactive').prop('checked'));
        this._handleLastVisibleChild();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSearchInputKeyDown: function (ev) {
        // <Tab> or <Enter>
        if (ev.which === 13 || ev.which === 9) {
            this._searchScrollTo($(ev.currentTarget).val(), !ev.shiftKey);
            ev.preventDefault();
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSearchInputKeyInput: function (ev) {
        // Useful for input empty either with ms-clear or by typing
        if (ev.currentTarget.value === "") {
            this._searchScrollTo("");
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSearchButtonClick: function (ev) {
        this._searchScrollTo(this.$('.o_search input').val());
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onShowDiffClick: function (ev) {
        ev.preventDefault();
        this.do_action('base.reset_view_arch_wizard_action', {
            additional_context: {
                'active_model': 'ir.ui.view',
                'active_ids': [parseInt(ev.currentTarget.dataset['view_id'])],
            }
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onLoadHierarchyClick: function (ev) {
        ev.preventDefault();
        this.do_action('website.action_show_viewhierarchy', {
            additional_context: {
                'active_model': 'ir.ui.view',
                'active_id': parseInt(ev.currentTarget.dataset['view_id']),
            }
        });
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Adds a class to the last visible element of every lists.
     * This is purely cosmetic to add a right angle dashed `:before` style in
     * css. This can't be done in css as there is no way to target a last
     * element by class.
     *
     * @private
     */
    _handleLastVisibleChild: function () {
        this.$('.o_last_visible_child').removeClass('o_last_visible_child');
        const lastElements = _.filter(_.map(
            this.$('ul'), el => $(el).find('> li:visible').last()[0]
        ));
        $(lastElements).addClass('o_last_visible_child');

        const selector = $('#o_show_inactive').prop('checked') ? '> li' : '> li:not(.o_is_inactive)';
        this.$('.o_fold_icon').map(function () {
            let $ico = $(this);
            let childs = $ico.parent().parent().first().find('ul').find(selector);
            $ico.toggleClass('d-none', !childs.length);
        });
    },
    /**
     * Searches and scrolls to view entries matching the given text. Exact
     * matches will be returned first. Search is done on `key`, `id` and `name`
     * for exact matches, and `key`, `name` for simple matches.
     *
     * @private
     * @param {string} search text to search and scroll to
     * @param {boolean} [forward] set to false to go to previous find
     */
    _searchScrollTo: function (search, forward = true) {
        const foundClasses = 'o_search_found border border-info rounded px-2';
        this.$('.o_search_found').removeClass(foundClasses);
        this.$('.o_not_found').removeClass('o_not_found');
        this.$('.o_tab_hint').remove();
        if (search !== this.prevSearch) {
            this.prevSearch = search;
            this.cptFound = -1;
        }

        if (search) {
            // Exact match first
            const exactMatches = $(`[data-key="${search}" i], [data-id="${search}" i], [data-name="${search}" i]`).not(':hidden').get();
            let matches = $(`[data-key*="${search}" i], [data-name*="${search}" i]`).not(':hidden').not(exactMatches).get();
            matches = exactMatches.concat(matches);
            if (!matches.length) {
                this.$('.o_search input').addClass('o_not_found');
            } else {
                if (forward) {
                    this.cptFound++;
                    if (this.cptFound > matches.length - 1) {
                        this.cptFound = 0;
                    }
                } else {
                    this.cptFound--;
                    if (this.cptFound < 0) {
                        this.cptFound = matches.length - 1;
                    }
                }
                const el = matches[this.cptFound];
                $(el).children('p').addClass(foundClasses).append($('<span/>', {
                    class: 'o_tab_hint text-info ms-auto small fst-italic pe-2',
                    text: _.str.sprintf(_t("Press %s for next %s"), "<Tab>", `[${this.cptFound + 1}/${matches.length}]`),
                }));
                $('.o_content').scrollTo(el, 0, {offset: -200});

                this.prevSearch = search;
                this.$('.o_search input').focus();
            }
        }
    },
});

const ViewHierarchy = qweb.View.extend({
    withSearchBar: false,
    config: _.extend({}, qweb.View.prototype.config, {
        Renderer: Renderer,
    }),
});

viewRegistry.add('view_hierarchy', ViewHierarchy);
});
