/** @odoo-module  */

import { KeepLast } from "@web/core/utils/concurrency";
import publicWidget from '@web/legacy/js/public/public_widget';

import { rpc } from "@web/core/network/rpc";
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
    },


    start: function () {
        this.inputEl = this.el.querySelector(".search-query");
        this.url = this.el.dataset.acUrl;
        this.searchGroupEl = this.el.querySelector(".input-group");
        this.enabled = parseInt(this.el.dataset.autocomplete);

        return this._super.apply(this, arguments);
    },

    /**
     * @private
     */
    async _fetch() {
        const search = this.inputEl.value;
        if (!search || search.length < 3)
            return;

        return rpc(this.url, { 'term': search });
    },

    /**
     * @private
     */
    _render: function (res) {
        const prevMenuEl = this.menuEl;
        const search = this.inputEl.value;
        this.el.classList.toggle("dropdown", !!res);
        this.el.classList.toggle("show", !!res);
        if (!!res) {
            this.menuEl = renderToElement("website_helpdesk.knowledge_base_autocomplete", {
                results: res.results,
                showMore: res.showMore,
                term: search,
            });
            this.searchGroupEl.dataset.bsToggle = "dropdown";
            this.el.append(this.menuEl);
        } else {
            // Avoid error with empty dropdown
            this.searchGroupEl.dataset.bsToggle = null;
        }
        if (prevMenuEl) {
            prevMenuEl.remove();
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
        if (!this.el.contains(document.activeElement)) {
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
                if (this.menuEl) {
                    const element =
                        ev.key === "ArrowUp"
                            ? this.menuEl.lastElementChild
                            : this.menuEl.firstElementChild;
                    element.focus();
                }
                break;
        }
    },
});
