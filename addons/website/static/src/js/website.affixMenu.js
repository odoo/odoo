odoo.define('website.affixMenu', function (require) {
"use strict";

    require('web_editor.ready');
    var snippetAnimation = require('website.content.snippets.animation');
    var self            = $(this),
        $header         = $('header'),
        $headerClone    = null,
        headerAffix     = false,
        $win            = $(window);

    if ($header.hasClass('top_menu_affix')) {
        headerAffix = true;
        var $headerClone = $header.clone().insertAfter($header).attr('class', 'o_header_affix affix');
        // Handle events for the collapsible menus
        $headerClone.find('[data-toggle="collapse"]').each(function () {
            var source = $(this),
                    targetClass = source.attr("data-target"),
                    target = $headerClone.find(targetClass),
                    className = targetClass.substring(1);
            source.attr("data-target", targetClass + "_clone");
            target.removeClass(className).addClass(className + "_clone" );
        })
    }

    $win.load(function () {})
    // Resize
    .on('resize', function () {
        $win.trigger('scroll');
    }) // Scroll
    .on("scroll", function () {
        if (headerAffix) {
            var wOffset  = $win.scrollTop();
            var hOffset  = $header.scrollTop();
            if(wOffset > (hOffset + 300)) {
                $headerClone.addClass("affixed");
                // reset opened menus on scroll down
                $header.find('.dropdown').removeClass('open');
                $header.find('.navbar-collapse').removeClass('in').attr('aria-expanded', false);
            }
            else {
                $headerClone.removeClass("affixed");
                // reset opened menus on scroll up
                $headerClone.find('.dropdown').removeClass('open');
                $headerClone.find('.navbar-collapse').removeClass('in').attr('aria-expanded', false);
            }
        }
    })
    .trigger('resize');

    // Remove affix-menu in Editor
    snippetAnimation.registry.editorInit = snippetAnimation.Class.extend({
        selector : ".o_header_affix",
        destroy: function () {
            this.$el.remove();
            return this._super.apply(this, arguments);
        },
    });
});
