odoo.define('website.s_blockquote_options', function (require) {
'use strict';

const options = require('web_editor.snippets.options');

options.registry.Blockquote = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Changes the position of the progressbar text.
     *
     * @see this.selectClass for parameters
     */
    display: function (previewMode, widgetValue, params) {
        this.$target.find('.s_blockquote_icon')
            .toggleClass('d-none', widgetValue !== 'classic');

        const $content = this.$target.find('.s_blockquote_content');
        $content.find('.quote_char').remove();
        if (widgetValue === 'cover') {
            this.$target.find('.s_blockquote_content > p').before(
                $('<fa/>').addClass('quote_char fa fa-quote-left font-italic')
            );
        }

        // Text style
        $content.toggleClass('text-center', widgetValue === 'cover');
        $content.toggleClass('font-italic', widgetValue !== 'classic');

        // Bg Img
        if (widgetValue === 'cover') {
            this.$target.css({'background-image': "url('/web/image/website.s_parallax_default_image')"});
            this.$target.css({'background-position': "50%"});
            $content.css({'background-color': "rgba(0, 0, 0, 0.5)"});
        } else {
            this.$target.css({'background-image': "unset"});
            $content.css({'background-color': "unset"});
        }

        // Blockquote Footer
        const $footer = this.$target.find('footer');
        $footer.toggleClass('text-white', widgetValue === 'cover');
        this.$target.toggleClass('text-white', widgetValue === 'cover');
        $footer.toggleClass('d-none', widgetValue === 'minimalist');
        this.$target.find('.s_blockquote_avatar')
            .toggleClass('d-none', widgetValue !== 'classic');
    },
});
});
