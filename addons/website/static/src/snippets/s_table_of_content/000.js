odoo.define('website.s_table_of_content', function (require) {
'use strict';

const publicWidget = require('web.public.widget');
const {extraMenuUpdateCallbacks} = require('website.content.menu');

const TableOfContent = publicWidget.Widget.extend({
    selector: 'section .s_table_of_content_navbar_sticky',
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.$scrollingElement = $().getScrollingElement();
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
        this.$target.css('top', '');
        this.$target.find('.s_table_of_content_navbar').css({top: '', maxHeight: ''});
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateTableOfContentNavbarPosition() {
        if (!this.$target[0].querySelector('a.table_of_content_link')) {
            // Do not start the scrollspy if the TOC is empty.
            return;
        }
        let position = 0;
        const $fixedElements = $('.o_top_fixed_element');
        _.each($fixedElements, el => position += $(el).outerHeight());
        const isHorizontalNavbar = this.$target.hasClass('s_table_of_content_horizontal_navbar');
        this.$target.css('top', isHorizontalNavbar ? position : '');
        this.$target.find('.s_table_of_content_navbar').css('top', isHorizontalNavbar ? '' : position + 20);
        position += isHorizontalNavbar ? this.$target.outerHeight() : 0;
        this.$target.find('.s_table_of_content_navbar').css('maxHeight', isHorizontalNavbar ? '' : `calc(100vh - ${position + 40}px)`);
        if (this.previousPosition !== position) {
            new ScrollSpy(this.$scrollingElement, {
                target: this.$target.find('.s_table_of_content_navbar'),
                method: 'offset',
                offset: position + 100,
                alwaysKeepFirstActive: true,
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

return TableOfContent;
});
