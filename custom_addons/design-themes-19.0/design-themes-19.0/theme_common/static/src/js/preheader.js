/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import "@website/js/content/menu";

publicWidget.registry.StandardAffixedHeader.include({
    /**
     * @override
     */
    start: function () {
        this.$preheader = this.$el.find('#o_theme_preheader');
        this.preheaderVisible = this.$preheader.css('display') !== 'none';
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this.$el.find('#o_theme_preheader').show();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _updateHeaderOnScroll: function (scrollTop) {
        var def = this._super.apply(this, arguments);
        if (this.preheaderVisible) {
            if (this.$el.hasClass('o_header_is_scrolled')) {
                this.$el.find('#o_theme_preheader').hide();
            } else {
                this.$el.find('#o_theme_preheader').show(200);
            }
        }
        return def;
    }
});
publicWidget.registry.FixedHeader.include({
    /**
     * @override
     */
    start: function () {
        this.$preheader = this.$el.find('#o_theme_preheader');
        this.preheaderVisible = this.$preheader.css('display') !== 'none';
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this.$el.css('transform', '');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _updateHeaderOnScroll: function (scrollTop) {
        var def = this._super.apply(this, arguments);
        if (this.preheaderVisible) {
            if (this.$el.hasClass('o_header_is_scrolled')) {
                if (!this.$el.hasClass('o_header_disappears') && !this.$el.hasClass('o_header_fade_out')) {
                    const preheaderHeight = this.$el.find('#o_theme_preheader').outerHeight();
                    this.$el.css('transform', 'translate(0, -' + preheaderHeight + 'px)');
                }
            } else {
                this.$el.css('transform', '');
            }
        }
        return def;
    }
});

const BaseDisappearingPreheader = {
    /**
     * @override
     */
    start: function () {
        this.$preheader = this.$el.find('#o_theme_preheader');
        this.preheaderVisible = this.$preheader.css('display') !== 'none';
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _showHeader: function () {
        var def = this._super.apply(this, arguments);
        if (this.preheaderVisible) {
            const preheaderHeight = this.$preheader.outerHeight();
            if (this.$el.hasClass('o_header_is_scrolled')) {
                this.$el.css('transform', 'translate(0, -' + preheaderHeight + 'px)');
            }
        }
        return def;
    }
};

publicWidget.registry.DisappearingHeader.include(BaseDisappearingPreheader);
publicWidget.registry.FadeOutHeader.include(BaseDisappearingPreheader);
