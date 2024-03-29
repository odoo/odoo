/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import {extraMenuUpdateCallbacks} from "@website/js/content/menu";

const TableOfContent = publicWidget.Widget.extend({
    selector: 'section .s_table_of_content_navbar_sticky',
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        this._stripNavbarStyles();
        await this._super(...arguments);
        this.$scrollingElement = this.$target.closest(".s_table_of_content").closestScrollable();
        this.previousPosition = -1;
        this._updateTableOfContentNavbarPosition();
        this._updateTableOfContentNavbarPositionBound = this._updateTableOfContentNavbarPosition.bind(this);
        extraMenuUpdateCallbacks.push(this._updateTableOfContentNavbarPositionBound);
    },
    /**
     * @override
     */
    destroy() {
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
            new ScrollSpy(this.$scrollingElement, {
                target: this.$el.find('.s_table_of_content_navbar'),
                method: 'offset',
                offset: position + 100,
                alwaysKeepFirstActive: true
            });
            this.previousPosition = position;
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
