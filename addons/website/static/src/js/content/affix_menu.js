odoo.define('website.content.affix_menu', function (require) {
'use strict';

var sAnimation = require('website.content.snippets.animation');

sAnimation.registry.affixMenu = sAnimation.Class.extend({
    selector: 'header.o_affix_enabled',

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        if (this.editableMode) {
            return def;
        }

        var self = this;
        this.$headerClone = this.$target.clone().attr('class', 'o_header_affix affix');
        this.$headerClone.insertAfter(this.$target);
        this.$headers = this.$target.add(this.$headerClone);
        this.$dropdowns = this.$headers.find('.dropdown');
        this.$navbarCollapses = this.$headers.find('.navbar-collapse');

        // Handle events for the collapse menus
        _.each(this.$headerClone.find('[data-toggle="collapse"]'), function (el) {
            var $source = $(el);
            var targetClass = $source.attr('data-target');
            var $target = self.$headerClone.find(targetClass);
            var className = targetClass.substring(1);
            $source.attr('data-target', targetClass + '_clone');
            $target.removeClass(className).addClass(className + '_clone');
        });

        // Window Handlers
        $(window).on('resize.affixMenu scroll.affixMenu', _.throttle(this._onWindowUpdate.bind(this), 200));
        setTimeout(this._onWindowUpdate.bind(this), 0); // setTimeout to allow override with advanced stuff... see themes

        return def;
    },
    /**
     * @override
     */
    destroy: function () {
        if (this.$headerClone) {
            this.$headerClone.remove();
            $(window).off('.affixMenu');
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the window is resized or scrolled -> updates affix status and
     * automatically closes submenus.
     *
     * @private
     */
    _onWindowUpdate: function () {
        var wOffset = $(window).scrollTop();
        var hOffset = this.$target.scrollTop();
        this.$headerClone.toggleClass('affixed', wOffset > (hOffset + 300));

        // Reset opened menus
        this.$dropdowns.removeClass('open');
        this.$navbarCollapses.removeClass('in').attr('aria-expanded', false);
    },
});
});
