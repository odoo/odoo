/** @odoo-module **/

import concurrency from 'web.concurrency';
import publicWidget from 'web.public.widget';

import {qweb} from 'web.core';
import {Markup} from 'web.utils';

publicWidget.registry.searchBar = publicWidget.Widget.extend({
    selector: '.o_searchbar_form',
    xmlDependencies: ['/website/static/src/snippets/s_searchbar/000.xml'],
    events: {
        'input .search-query': '_onInput',
        'focusout': '_onFocusOut',
        'keydown .search-query': '_onKeydown',
        'search .search-query': '_onSearch',
    },
    autocompleteMinWidth: 300,

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this._dp = new concurrency.DropPrevious();

        this._onInput = _.debounce(this._onInput, 400);
        this._onFocusOut = _.debounce(this._onFocusOut, 100);
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
                    this.options[key] = value;
                }
            }
        }
        const pathParts = urlPath.split('/');
        for (const index in pathParts) {
            const value = pathParts[index];
            if (index > 0 && /-[0-9]+$/.test(value)) { // is sluggish
                this.options[pathParts[index - 1]] = value;
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
        const res = await this._rpc({
            route: '/website/snippet/autocomplete',
            params: {
                'search_type': this.searchType,
                'term': this.$input.val(),
                'order': this.order,
                'limit': this.limit,
                'max_nb_chars': Math.round(Math.max(this.autocompleteMinWidth, parseInt(this.$el.width())) * 0.22),
                'options': this.options,
            },
        });
        const fieldNames = [
            'name',
            'description',
            'extra_link',
            'detail',
            'detail_strike',
            'detail_extra',
        ];
        res.results.forEach(record => {
            for (const fieldName of fieldNames) {
                if (record[fieldName]) {
                    if (typeof record[fieldName] === "object") {
                        for (const fieldKey of Object.keys(record[fieldName])) {
                            record[fieldName][fieldKey] = Markup(record[fieldName][fieldKey]);
                        }
                    } else {
                        record[fieldName] = Markup(record[fieldName]);
                    }
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

        const $prevMenu = this.$menu;
        this.$el.toggleClass('dropdown show', !!res);
        if (res && this.limit) {
            const results = res['results'];
            let template = 'website.s_searchbar.autocomplete';
            const candidate = template + '.' + this.searchType;
            if (qweb.has_template(candidate)) {
                template = candidate;
            }
            this.$menu = $(qweb.render(template, {
                results: results,
                parts: res['parts'],
                hasMoreResults: results.length < res['results_count'],
                search: this.$input.val(),
                fuzzySearch: res['fuzzy_search'],
                widget: this,
            }));

            // TODO adapt directly in the template in master
            const mutedItemTextEl = this.$menu.find('span.dropdown-item-text.text-muted')[0];
            if (mutedItemTextEl) {
                const newItemTextEl = document.createElement('span');
                newItemTextEl.classList.add('dropdown-item-text');
                mutedItemTextEl.after(newItemTextEl);
                mutedItemTextEl.classList.remove('dropdown-item-text');
                newItemTextEl.appendChild(mutedItemTextEl);
            }

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

        if ($prevMenu) {
            $prevMenu.remove();
        }
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
            this._dp.add(this._fetch()).then(this._render.bind(this));
        }
    },
    /**
     * @private
     */
    _onFocusOut: function () {
        if (!this.$el.has(document.activeElement).length) {
            this._render();
        }
    },
    /**
     * @private
     */
    _onKeydown: function (ev) {
        switch (ev.which) {
            case $.ui.keyCode.ESCAPE:
                this._render();
                break;
            case $.ui.keyCode.UP:
            case $.ui.keyCode.DOWN:
                ev.preventDefault();
                if (this.$menu) {
                    let $element = ev.which === $.ui.keyCode.UP ? this.$menu.children().last() : this.$menu.children().first();
                    $element.focus();
                }
                break;
            case $.ui.keyCode.ENTER:
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
