/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import {extraMenuUpdateCallbacks} from "@website/js/content/menu";
import { closestScrollable } from "@web_editor/js/common/scrolling";

const CLASS_NAME_DROPDOWN_ITEM = 'dropdown-item';
const CLASS_NAME_ACTIVE = 'active';
const SELECTOR_NAV_LIST_GROUP = '.nav, .list-group';
const SELECTOR_NAV_LINKS = '.nav-link';
const SELECTOR_NAV_ITEMS = '.nav-item';
const SELECTOR_LIST_ITEMS = '.list-group-item';
const SELECTOR_LINK_ITEMS = `${SELECTOR_NAV_LINKS}, ${SELECTOR_LIST_ITEMS}, .${CLASS_NAME_DROPDOWN_ITEM}`;
const SELECTOR_DROPDOWN = '.dropdown';
const SELECTOR_DROPDOWN_TOGGLE = '.dropdown-toggle';

const getSelector = element => {
    let hrefAttr = element.getAttribute('href');
    if (!hrefAttr || !hrefAttr.startsWith('#')) {
        return null;
    }
    const selector = hrefAttr && hrefAttr !== '#' ? hrefAttr.trim() : null;
    return selector;
};

const parents = (element, selector) => {
    const parents = [];
    let ancestor = element.parentNode.closest(selector);
    while (ancestor) {
        parents.push(ancestor);
        ancestor = ancestor.parentNode.closest(selector);
    }
    return parents;
};

const prev = (element, selector) => {
    let previous = element.previousElementSibling;
    while (previous) {
        if (previous.matches(selector)) {
            return [previous];
        }
        previous = previous.previousElementSibling;
    }
    return [];
};

const TableOfContent = publicWidget.Widget.extend({
    selector: 'section .s_table_of_content_navbar_sticky',
    disabledInEditableMode: false,

    init() {
        this._super(...arguments);
        this._onScrollBound = this._process.bind(this);
        this._offsets = [];
        this._targets = [];
        this._activeTarget = null;
        this._scrollHeight = 0;
        this._offset = 0;
    },

    /**
     * @override
     */
    async start() {
        this._stripNavbarStyles();
        this._scrollElement = closestScrollable(this.$target.closest(".s_table_of_content")[0]);
        this._scrollTarget = $().getScrollingTarget(this._scrollElement)[0];
        this._tocElement = this.el.querySelector('.s_table_of_content_navbar');
        this.previousPosition = -1;
        this._updateTableOfContentNavbarPosition();
        this._updateTableOfContentNavbarPositionBound = this._updateTableOfContentNavbarPosition.bind(this);
        extraMenuUpdateCallbacks.push(this._updateTableOfContentNavbarPositionBound);
        this._scrollTarget.addEventListener("scroll", this._onScrollBound);
        await this._super(...arguments);
    },
    /**
     * @override
     */
    destroy() {
        this._scrollTarget?.removeEventListener("scroll", this._onScrollBound);
        const indexCallback = extraMenuUpdateCallbacks.indexOf(this._updateTableOfContentNavbarPositionBound);
        if (indexCallback >= 0) {
            extraMenuUpdateCallbacks.splice(indexCallback, 1);
        }
        this.$el.css('top', '');
        this.$el.find('.s_table_of_content_navbar').css({top: '', maxHeight: ''});
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _stripNavbarStyles() {
        // This is needed for styles added on translations when the master text
        // has no style.
        for (let el of this.el.querySelectorAll('.s_table_of_content_navbar .table_of_content_link')) {
            const translationEl = el.querySelector('span[data-oe-translation-state]');
            if (translationEl) {
                el = translationEl;
            }
            const text = el.textContent; // Get text from el.
            el.textContent = text; // Replace all of el's content with that text.
        }
    },
    /**
     * @private
     */
    _updateTableOfContentNavbarPosition() {
        if (!this.el.querySelector('a.table_of_content_link')) {
            // Do not start the scrollspy if the TOC is empty.
            return;
        }
        let position = 0;
        const $fixedElements = $('.o_top_fixed_element');
        $fixedElements.toArray().forEach((el) => position += $(el).outerHeight());
        const isHorizontalNavbar = this.$el.hasClass('s_table_of_content_horizontal_navbar');
        this.$el.css('top', isHorizontalNavbar ? position : '');
        this.$el.find('.s_table_of_content_navbar').css('top', isHorizontalNavbar ? '' : position + 20);
        position += isHorizontalNavbar ? this.$el.outerHeight() : 0;
        this.$el.find('.s_table_of_content_navbar').css('maxHeight', isHorizontalNavbar ? '' : `calc(100vh - ${position + 40}px)`);
        if (this.previousPosition !== position) {
            this._offset = position + 100;
            this._refresh();
            this._process();
            this.previousPosition = position;
        }
    },

    _getScrollHeight() {
        return this._scrollElement.scrollHeight || Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
    },

    _refresh() {
        this._offsets = [];
        this._targets = [];
        this._scrollHeight = this._getScrollHeight();
        const targets = [...this._tocElement.querySelectorAll(SELECTOR_LINK_ITEMS)];
        targets.map(element => {
            const targetSelector = getSelector(element);
            const target = targetSelector ? document.querySelector(targetSelector) : null;
            if (target) {
                const targetBCR = target.getBoundingClientRect();

                if (targetBCR.width || targetBCR.height) {
                    return [targetBCR.top, targetSelector];
                }
            }
            return null;
        }).filter(item => item).sort((a, b) => a[0] - b[0]).forEach(item => {
            this._offsets.push(item[0]);
            this._targets.push(item[1]);
        });
        const baseScrollTop = this._scrollElement.scrollTop;
        for (let i = 0; i < this._offsets.length; i++) {
            this._offsets[i] += baseScrollTop;
        }
    },

    _activate(target) {
        const element = document.querySelector(`[href="${target}"]`);
        if (!element || $(element).is(':hidden')) {
            return;
        }
        this._activeTarget = target;
        this._clear();
        const queries = SELECTOR_LINK_ITEMS.split(',').map(selector => `${selector}[href="${target}"]`);
        const link = this._tocElement.querySelector(queries.join(','));
        link.classList.add(CLASS_NAME_ACTIVE);
        if (link.classList.contains(CLASS_NAME_DROPDOWN_ITEM)) {
            link.closest(SELECTOR_DROPDOWN).querySelector(SELECTOR_DROPDOWN_TOGGLE, link.closest(SELECTOR_DROPDOWN)).classList.add(CLASS_NAME_ACTIVE);
        } else {
            parents(link, SELECTOR_NAV_LIST_GROUP).forEach(listGroup => {
                // Set triggered links parents as active
                // With both <ul> and <nav> markup a parent is the previous sibling of any nav ancestor
                prev(listGroup, `${SELECTOR_NAV_LINKS}, ${SELECTOR_LIST_ITEMS}`).forEach(item => item.classList.add(CLASS_NAME_ACTIVE)); // Handle special case when .nav-link is inside .nav-item
                prev(listGroup, SELECTOR_NAV_ITEMS).forEach(navItem => {
                    [...navItem.children].filter(child => child.matches(SELECTOR_NAV_LINKS)).forEach(item => item.classList.add(CLASS_NAME_ACTIVE));
                });
            });
        }
    },

    _clear() {
        [...this._tocElement.querySelectorAll(SELECTOR_LINK_ITEMS)].filter(node => node.classList.contains(CLASS_NAME_ACTIVE)).forEach(node => node.classList.remove(CLASS_NAME_ACTIVE));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _process() {
        const scrollTop = this._scrollElement.scrollTop + this._offset;
        const scrollHeight = this._getScrollHeight();
        const maxScroll = this._offset + scrollHeight - this._scrollElement.getBoundingClientRect().height;
        if (this._scrollHeight !== scrollHeight) {
            this._refresh();
        }
        if (scrollTop >= maxScroll) {
            const target = this._targets[this._targets.length - 1];
            if (this._activeTarget !== target) {
                this._activate(target);
            }
            return;
        }
        if (this._activeTarget && scrollTop < this._offsets[0] && this._offsets[0] > 0) {
            this._activeTarget = null;
            this._clear();
        } else {
            for (let i = this._offsets.length; i--;) {
                const isActiveTarget = this._activeTarget !== this._targets[i] && scrollTop >= this._offsets[i] && (typeof this._offsets[i + 1] === 'undefined' || scrollTop < this._offsets[i + 1]);

                if (isActiveTarget) {
                    this._activate(this._targets[i]);
                }
            }
        }
        if (this._activeTarget === null) {
            this._activate(this._targets[0]);
        }
    },
});

publicWidget.registry.anchorSlide.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Overridden to add the height of the horizontal sticky navbar at the scroll value
     * when the link is from the table of content navbar
     *
     * @override
     * @private
     */
    _computeExtraOffset() {
        let extraOffset = this._super(...arguments);
        if (this.$el.hasClass('table_of_content_link')) {
            const tableOfContentNavbarEl = this.$el.closest('.s_table_of_content_navbar_sticky.s_table_of_content_horizontal_navbar');
            if (tableOfContentNavbarEl.length > 0) {
                extraOffset += $(tableOfContentNavbarEl).outerHeight();
            }
        }
        return extraOffset;
    },
});

publicWidget.registry.snippetTableOfContent = TableOfContent;

export default TableOfContent;
