/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

options.registry.Blockquote = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Change blockquote design.
     *
     * @see this.selectClass for parameters
     */
    display: function (previewMode, widgetValue, params) {

        // Classic
        this.$target.find('.s_blockquote_avatar').toggleClass('d-none', widgetValue !== 'classic');

        // Cover
        const $blockquote = this.$target.find('.s_blockquote_content');
        if (widgetValue === 'cover') {
            $blockquote.css({"background-image": "url('/web/image/website.s_blockquote_cover_default_image')"});
            $blockquote.addClass('oe_img_bg o_bg_img_center');
            if (!$blockquote.find('.o_we_bg_filter').length) {
                const bgFilterEl = document.createElement('div');
                bgFilterEl.classList.add('o_we_bg_filter', 'bg-white-50');
                $blockquote.prepend(bgFilterEl);
            }
        } else {
            $blockquote.css({"background-image": ""});
            $blockquote.css({"background-position": ""});
            $blockquote.removeClass('oe_img_bg o_bg_img_center');
            $blockquote.find('.o_we_bg_filter').remove();
            $blockquote.find('.s_blockquote_filter').contents().unwrap(); // Compatibility
        }

        // Minimalist
        this.$target.find('.s_blockquote_icon').toggleClass('d-none', widgetValue === 'minimalist');
        this.$target.find('footer').toggleClass('d-none', widgetValue === 'minimalist');
    },
});
