/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";
import publicWidget from '@web/legacy/js/public/public_widget';

import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { renderToElement, renderToString } from "@web/core/utils/render";
import { debounce } from '@web/core/utils/timing';

import { markup } from "@odoo/owl";

publicWidget.registry.searchBar = publicWidget.Widget.extend({
    selector: '.o_searchbar_form',
    events: {
        'input .search-query': '_onInput',
        'focusout': '_onFocusOut',
        "mousedown .o_dropdown_menu .dropdown-item": "_onMousedown",
        "mouseup .o_dropdown_menu .dropdown-item": "_onMouseup",
        'keydown .search-query, .dropdown-item': '_onKeydown',
        'search .search-query': '_onSearch',
    },
    autocompleteMinWidth: 300,

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this.keepLast = new KeepLast();

        this._onInput = debounce(this._onInput, 400);
        this._onFocusOut = debounce(this._onFocusOut, 100);
    },
    /**
     * @override
     */
    start: function () {
        this.$input = this.$('.search-query');

        this.searchType = this.$input.data('searchType');
        this.order = this.$('.o_search_order_by').val();
        this.limit = parseInt(this.$input.data('limit'));
        this.displayDescription = this.$input.data('displayDescription');
        this.displayExtraLink = this.$input.data('displayExtraLink');
        this.displayDetail = this.$input.data('displayDetail');
        this.displayImage = this.$input.data('displayImage');
        this.wasEmpty = !this.$input.val();
        // Make it easy for customization to disable fuzzy matching on specific searchboxes
        this.allowFuzzy = !this.$input.data('noFuzzy');
        if (this.limit) {
            this.$input.attr('autocomplete', 'off');
        }

        this.options = {
            'displayImage': this.displayImage,
            'displayDescription': this.displayDescription,
            'displayExtraLink': this.displayExtraLink,
            'displayDetail': this.displayDetail,
            'allowFuzzy': this.allowFuzzy,
        };
        const form = this.$('.o_search_order_by').parents('form');
        for (const field of form.find("input[type='hidden']")) {
            this.options[field.name] = field.value;
        }
        const action = form.attr('action') || window.location.pathname + window.location.search;
        const [urlPath, urlParams] = action.split('?');
        if (urlParams) {
            for (const keyValue of urlParams.split('&')) {
                const [key, value] = keyValue.split('=');
                if (value && key !== 'search') {
                    // Decode URI parameters: revert + to space then decodeURIComponent.
                    this.options[decodeURIComponent(key.replace(/\+/g, '%20'))] = decodeURIComponent(value.replace(/\+/g, '%20'));
                }
            }
        }
        const pathParts = urlPath.split('/');
        for (const index in pathParts) {
            const value = decodeURIComponent(pathParts[index]);
            if (index > 0 && /-[0-9]+$/.test(value)) { // is sluggish
                this.options[decodeURIComponent(pathParts[index - 1])] = value;
            }
        }

        if (this.$input.data('noFuzzy')) {
            $("<input type='hidden' name='noFuzzy' value='true'/>").appendTo(this.$input);
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this._render(null);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptToScrollingParent() {
        const bcr = this.el.getBoundingClientRect();
        this.$menu[0].style.setProperty('position', 'fixed', 'important');
        this.$menu[0].style.setProperty('top', `${bcr.bottom}px`, 'important');
        this.$menu[0].style.setProperty('left', `${bcr.left}px`, 'important');
        this.$menu[0].style.setProperty('max-width', `${bcr.width}px`, 'important');
        this.$menu[0].style.setProperty('max-height', `${document.body.clientHeight - bcr.bottom - 16}px`, 'important');
    },
    /**
     * @private
     */
    async _fetch() {
        const res = await rpc('/website/snippet/autocomplete', {
            'search_type': this.searchType,
            'term': this.$input.val(),
            'order': this.order,
            'limit': this.limit,
            'max_nb_chars': Math.round(Math.max(this.autocompleteMinWidth, parseInt(this.$el.width())) * 0.22),
            'options': this.options,
        });
        const fieldNames = this._getFieldsNames();
        res.results.forEach(record => {
            for (const fieldName of fieldNames) {
                if (record[fieldName]) {
                    record[fieldName] = markup(record[fieldName]);
                }
            }
        });
        return res;
    },
    /**
     * @private
     */
    _render: function (res) {
        if (this._scrollingParentEl) {
            this._scrollingParentEl.removeEventListener('scroll', this._menuScrollAndResizeHandler);
            window.removeEventListener('resize', this._menuScrollAndResizeHandler);
            delete this._scrollingParentEl;
            delete this._menuScrollAndResizeHandler;
        }

        let pageScrollHeight = null;
        const $prevMenu = this.$menu;
        if (res && this.limit) {
            const results = res['results'];
            let template = 'website.s_searchbar.autocomplete';
            const candidate = template + '.' + this.searchType;
            if (renderToString.app.getRawTemplate(candidate)) {
                template = candidate;
            }
            this.$menu = $(renderToElement(template, {
                results: results,
                parts: res['parts'],
                hasMoreResults: results.length < res['results_count'],
                search: this.$input.val(),
                fuzzySearch: res['fuzzy_search'],
                widget: this,
            }));
            this.$menu.css('min-width', this.autocompleteMinWidth);

            // Handle the case where the searchbar is in a mega menu by making
            // it position:fixed and forcing its size. Note: this could be the
            // default behavior or at least needed in more cases than the mega
            // menu only (all scrolling parents). But as a stable fix, it was
            // easier to fix that case only as a first step, especially since
            // this cannot generically work on all scrolling parent.
            const megaMenuEl = this.el.closest('.o_mega_menu');
            if (megaMenuEl) {
                const navbarEl = this.el.closest('.navbar');
                const navbarTogglerEl = navbarEl ? navbarEl.querySelector('.navbar-toggler') : null;
                if (navbarTogglerEl && navbarTogglerEl.clientWidth < 1) {
                    this._scrollingParentEl = megaMenuEl;
                    this._menuScrollAndResizeHandler = () => this._adaptToScrollingParent();
                    this._scrollingParentEl.addEventListener('scroll', this._menuScrollAndResizeHandler);
                    window.addEventListener('resize', this._menuScrollAndResizeHandler);

                    this._adaptToScrollingParent();
                }
            }

            pageScrollHeight = document.documentElement.scrollHeight;
            this.$el.append(this.$menu);

            this.$el.find('button.extra_link').on('click', function (event) {
                event.preventDefault();
                window.location.href = event.currentTarget.dataset['target'];
            });
            this.$el.find('.s_searchbar_fuzzy_submit').on('click', (event) => {
                event.preventDefault();
                this.$input.val(res['fuzzy_search']);
                const form = this.$('.o_search_order_by').parents('form');
                form.submit();
            });
        }

        this.$el.toggleClass('dropdown show', !!res);
        if ($prevMenu) {
            $prevMenu.remove();
        }
        // Adjust the menu's position based on the scroll height.
        if (res && this.limit) {
            this.el.classList.remove("dropup");
            delete this.$menu[0].dataset.bsPopper;
            if (document.documentElement.scrollHeight > pageScrollHeight) {
                // If the menu overflows below the page, we reduce its height.
                this.$menu[0].style.maxHeight = "40vh";
                this.$menu[0].style.overflowY = "auto";
                // We then recheck if the menu still overflows below the page.
                if (document.documentElement.scrollHeight > pageScrollHeight) {
                    // If the menu still overflows below the page after its height
                    // has been reduced, we position it above the input.
                    this.el.classList.add("dropup");
                    this.$menu[0].dataset.bsPopper = "";
                }
            }
        }
    },
    _getFieldsNames() {
        return [
            'description',
            'detail',
            'detail_extra',
            'detail_strike',
            'extra_link',
            'name',
        ];
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onInput: function () {
        if (!this.limit) {
            return;
        }
        if (this.searchType === 'all' && !this.$input.val().trim().length) {
            this._render();
        } else {
            this.keepLast.add(this._fetch()).then(this._render.bind(this));
        }
    },
    /**
     * @private
     */
    _onFocusOut: function () {
        if (!this.linkHasFocus && !this.$el.has(document.activeElement).length) {
            this._render();
        }
    },
    _onMousedown(ev) {
        // On Safari, links and buttons are not focusable by default. We need
        // to get around that behavior to avoid _onFocusOut() from triggering
        // _render(), as this would prevent the click from working.
        if (isBrowserSafari) {
            this.linkHasFocus = true;
        }
    },
    _onMouseup(ev) {
        // See comment in _onMousedown.
        if (isBrowserSafari) {
            this.linkHasFocus = false;
        }
    },
    /**
     * @private
     */
    _onKeydown: function (ev) {
        switch (ev.key) {
            case "Escape":
                this._render();
                break;
            case "ArrowUp":
            case "ArrowDown":
                ev.preventDefault();
                if (this.$menu) {
                    const focusableEls = [this.$input[0], ...this.$menu[0].children];
                    const focusedEl = document.activeElement;
                    const currentIndex = focusableEls.indexOf(focusedEl) || 0;
                    const delta = ev.key === "ArrowUp" ? focusableEls.length - 1 : 1;
                    const nextIndex = (currentIndex + delta) % focusableEls.length;
                    const nextFocusedEl = focusableEls[nextIndex];
                    nextFocusedEl.focus();
                }
                break;
            case "Enter":
                this.limit = 0; // prevent autocomplete
                break;
        }
    },
    /**
     * @private
     */
    _onSearch: function (ev) {
        if (this.$input[0].value) { // actual search
            this.limit = 0; // prevent autocomplete
        } else { // clear button clicked
            this._render(); // remove existing suggestions
            ev.preventDefault();
            if (!this.wasEmpty) {
                this.limit = 0; // prevent autocomplete
                const form = this.$('.o_search_order_by').parents('form');
                form.submit();
            }
        }
    },
});

export default {
    searchBar: publicWidget.registry.searchBar,
};
