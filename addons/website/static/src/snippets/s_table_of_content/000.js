odoo.define('website.s_table_of_content', function (require) {
'use strict';

const publicWidget = require('web.public.widget');

const TableOfContent = publicWidget.Widget.extend({
    selector: 'section .s_table_of_content_navbar_sticky',
    disabledInEditableMode: false,

    /**
     * @override
     */
    start: function () {
        const $menuLoading = $('.o_menu_loading');
        if (!$menuLoading.length) {
            this._initializeNavbarTopPosition();
        } else {
            $(document.body).one('menu_loaded', () => this._initializeNavbarTopPosition());
        }
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this.$target.find('.s_table_of_content_navbar').css('top', '');
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Initialize the top position of the snippet navbar according to the height
     * of the headers of the page.
     * 
     * @private
     */
    _initializeNavbarTopPosition: function () {
        let headerHeight = 0;
        const $fixedElements = $('.o_top_fixed_element');
        const isHorizontalNavbar = this.$target.hasClass('s_table_of_content_horizontal_navbar');
        _.each($fixedElements, el => headerHeight += $(el).outerHeight());
        this.$target.css('top', isHorizontalNavbar ? headerHeight : '');
        this.$target.find('.s_table_of_content_navbar').css('top', !isHorizontalNavbar ? headerHeight : '');
        $('body').scrollspy({target: '.s_table_of_content_navbar', offset: headerHeight + 100});
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
    _computeHeaderHeight: function () {
        let headerHeight = this._super(...arguments);
        if (this.$el.hasClass('table_of_content_link')) {
            const tableOfContentNavbarEl = this.$el.closest('.s_table_of_content_navbar_sticky.s_table_of_content_horizontal_navbar');
            if (tableOfContentNavbarEl.length > 0) {
                headerHeight += $(tableOfContentNavbarEl).outerHeight();
            }
        }
        return headerHeight;
    },
});

publicWidget.registry.snippetTableOfContent = TableOfContent;

return TableOfContent;
});
