odoo.define("website.cookie_consent", function (require) {
    "use strict";

    var cookie_choices = require("web.cookie_choices");
    var sAnimation = require('website.content.snippets.animation');

    var CookiesForm = sAnimation.Class.extend({
        selector: "#cookies_form",
        events: _.extend({}, sAnimation.Class.prototype.events || {}, {
            'click .js_all': '_acceptAll',
        }),

        start: function () {
            return this._super.apply(this, arguments).then(this.proxy("_toggleBanner"));
        },

        _acceptAll: function () {
            this.$(":checkbox").prop("checked", true);
        },

        _toggleBanner: function () {
            var hidden = Boolean(this.editableMode || cookie_choices.allAcceptedCookies().length);
            this.$el.closest("#cookie_consent_banner").toggleClass("o_hidden", hidden);
        },
    });

    sAnimation.registry.cookies_form = CookiesForm;

    return {
        CookiesForm: CookiesForm,
    }
});
