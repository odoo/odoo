/** @odoo-module  */

import { KeepLast } from "@web/core/utils/concurrency";
import publicWidget from '@web/legacy/js/public/public_widget';

import { renderToElement } from "@web/core/utils/render";
import { debounce } from "@web/core/utils/timing";

publicWidget.registry.knowledgeBaseAutocomplete = publicWidget.Widget.extend({
    selector: '.o_helpdesk_knowledge_search',
    events: {
        'input .search-query': '_onInput',
        'focusout': '_onFocusOut',
        'keydown .search-query': '_onKeydown',
    },

    init: function () {
        this._super.apply(this, arguments);

        this.keepLast = new KeepLast();

        this._onInput = debounce(this._onInput, 400);
        this._onFocusOut = debounce(this._onFocusOut, 100);

        this.rpc = this.bindService("rpc");
    },


    start: function () {
        this.$input = this.$('.search-query');
        this.$url = this.$el.data('ac-url');
        this.enabled = this.$el.data('autocomplete');

        return this._super.apply(this, arguments);
    },

    /**
     * @private
     */
    async _fetch() {
        const search = this.$input.val();
        if (!search || search.length < 3)
            return;

        return this.rpc(this.$url, { 'term': search });
    },

    /**
     * @private
     */
    _render: function (res) {
        const $prevMenu = this.$menu;
        const search = this.$input.val();
        this.$el.toggleClass('dropdown show', !!res);
        if (!!res) {
            this.$menu = $(renderToElement('website_helpdesk.knowledge_base_autocomplete', {
                results: res.results,
                showMore: res.showMore,
                term: search,
            }));
            this.$el.append(this.$menu);
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
        if (!this.enabled)
            return;
        this.keepLast.add(this._fetch()).then(this._render.bind(this));
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
        switch (ev.key) {
            case "Escape":
                this._render();
                break;
            case "ArrowUp":
            case "ArrowDown":
                ev.preventDefault();
                if (this.$menu) {
                    let $element = ev.key === "ArrowUp" ? this.$menu.children().last() : this.$menu.children().first();
                    $element.focus();
                }
                break;
        }
    },
});
