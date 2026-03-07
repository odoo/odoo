/* global clearTimeout, setTimeout */

/* Copyright 2023 Taras Shabaranskyi
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {ControlPanel} from "@web/search/control_panel/control_panel";
import {browser} from "@web/core/browser/browser";
import {patch} from "@web/core/utils/patch";

export const STICKY_CLASS = "o_mobile_sticky";

/**
 * @param {Number} delay
 * @returns {{collect: function(Number, (function(Number, Number): void)): void}}
 */
export function minMaxCollector(delay = 100) {
    const state = {
        id: null,
        items: [],
    };

    function min() {
        return Math.min.apply(null, state.items);
    }

    function max() {
        return Math.max.apply(null, state.items);
    }

    return {
        collect(value, callback) {
            clearTimeout(state.id);
            state.items.push(value);
            state.id = setTimeout(() => {
                callback(min(), max());
                state.items = [];
                state.id = null;
            }, delay);
        },
    };
}

export const unpatchControlPanel = patch(ControlPanel.prototype, {
    scrollValueCollector: undefined,
    /** @type {Number}*/
    scrollHeaderGap: undefined,
    setup() {
        super.setup();
        this.scrollValueCollector = minMaxCollector(100);
        this.scrollHeaderGap = 2;
    },
    onScrollThrottled() {
        if (this.isScrolling) {
            return;
        }
        this.isScrolling = true;
        browser.requestAnimationFrame(() => (this.isScrolling = false));

        /** @type {HTMLElement}*/
        const rootEl = this.root.el;
        const scrollTop = this.getScrollingElement().scrollTop;
        const activeAnimation = scrollTop > this.initialScrollTop;

        rootEl.classList.toggle(STICKY_CLASS, activeAnimation);
        this.scrollValueCollector.collect(scrollTop - this.oldScrollTop, (min, max) => {
            const delta = min + max;
            if (delta < -this.scrollHeaderGap || delta > this.scrollHeaderGap) {
                rootEl.style.top = `${delta < 0 ? -rootEl.clientHeight : 0}px`;
            }
        });

        this.oldScrollTop = scrollTop;
    },
});
