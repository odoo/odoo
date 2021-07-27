odoo.define('root.widget', function (require) {
'use strict';

require('web.dom_ready');
var websiteRootData = require('website.WebsiteRoot');

var websiteRoot = new websiteRootData.WebsiteRoot(null);
return websiteRoot.attachTo(document.body).then(function () {
    return websiteRoot;
});
});

//==============================================================================

odoo.define('website.WebsiteRoot', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var Dialog = require('web.Dialog');
var utils = require('web.utils');
var BodyManager = require('web_editor.BodyManager');
var weContext = require('web_editor.context');
var rootWidget = require('web_editor.root_widget');
var sAnimation = require('website.content.snippets.animation');
require("website.content.zoomodoo");

var _t = core._t;

var websiteRootRegistry = new rootWidget.RootWidgetRegistry();

// Load localizations outside the WebsiteRoot to not wait for DOM ready (but
// wait for them in WebsiteRoot)
var lang = utils.get_cookie('frontend_lang') || weContext.get().lang; // FIXME the cookie value should maybe be in the ctx?
var localeDef = ajax.loadJS('/web/webclient/locale/' + lang.replace('-', '_'));

var WebsiteRoot = BodyManager.extend({
    events: _.extend({}, BodyManager.prototype.events || {}, {
        'click .js_change_lang': '_onLangChangeClick',
        'click .js_publish_management .js_publish_btn': '_onPublishBtnClick',
        'submit .js_website_submit_form': '_onWebsiteFormSubmit',
        'click .js_disable_on_click': '_onDisableOnClick',
        'click .js_multi_website_switch': '_multiWebsiteSwitch',
        'click .js_multi_company_switch': '_multiCompanySwitch',
    }),
    custom_events: _.extend({}, BodyManager.prototype.custom_events || {}, {
        animation_start_demand: '_onAnimationStartDemand',
        animation_stop_demand: '_onAnimationStopDemand',
        main_object_request: '_onMainObjectRequest',
        ready_to_clean_for_save: '_onAnimationStopDemand',
    }),

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this.animations = [];
    },
    /**
     * @override
     */
    willStart: function () {
        // TODO would be even greater to wait for localeDef only when necessary
        return $.when(this._super.apply(this, arguments), localeDef);
    },
    /**
     * @override
     */
    start: function () {
        var defs = [this._super.apply(this, arguments)];

        // Animations
        defs.push(this._startAnimations());

        // Compatibility lang change ?
        if (!this.$('.js_change_lang').length) {
            var $links = this.$('ul.js_language_selector li a:not([data-oe-id])');
            var m = $(_.min($links, function (l) {
                return $(l).attr('href').length;
            })).attr('href');
            $links.each(function () {
                var $link = $(this);
                var t = $link.attr('href');
                var l = (t === m) ? "default" : t.split('/')[1];
                $link.data('lang', l).addClass('js_change_lang');
            });
        }

        // Display image thumbnail
        this.$(".o_image[data-mimetype^='image']").each(function () {
            var $img = $(this);
            if (/gif|jpe|jpg|png/.test($img.data('mimetype')) && $img.data('src')) {
                $img.css('background-image', "url('" + $img.data('src') + "')");
            }
        });

        // Enable magnify on zommable img
        this.$('.zoomable img[data-zoom]').zoomOdoo();

        // Auto scroll
        if (window.location.hash.indexOf("scrollTop=") > -1) {
            this.el.scrollTop = +window.location.hash.match(/scrollTop=([0-9]+)/)[1];
        }

        // Fix for IE:
        if ($.fn.placeholder) {
            $('input, textarea').placeholder();
        }

        return $.when.apply($, defs);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * As the WebsiteRoot instance is designed to be unique, the associated
     * registry has been instantiated outside of the class and is simply
     * returned here.
     *
     * @private
     * @override
     */
    _getRegistry: function () {
        return websiteRootRegistry;
    },
    /**
     * Creates an Animation instance for each DOM element which matches the
     * `selector` key of one of the registered animations
     * (@see Animation.selector).
     *
     * @private
     * @param {boolean} [editableMode=false] - true if the page is in edition mode
     * @param {jQuery} [$from]
     *        only initialize the animations whose `selector` matches the
     *        element or one of its descendant (default to the wrapwrap element)
     * @returns {Deferred}
     */
    _startAnimations: function (editableMode, $from) {
        var self = this;

        editableMode = editableMode || false;
        if ($from === undefined) {
            $from = this.$('#wrapwrap');
        }

        this._stopAnimations($from);

        var defs = _.map(sAnimation.registry, function (Animation, animationName) {
            var selector = Animation.prototype.selector || '';
            var $target = $from.find(selector).addBack(selector);

            var defs = _.map($target, function (el) {
                var animation = new Animation(self, editableMode);
                self.animations.push(animation);
                return animation.attachTo($(el));
            });
            return $.when.apply($, defs);
        });
        return $.when.apply($, defs);
    },
    /**
     * Destroys all animation instances. Especially needed before saving while
     * in edition mode for example.
     *
     * @private
     * @param {jQuery} [$from]
     *        only stop the animations linked to the given element(s) or one of
     *        its descendants
     */
    _stopAnimations: function ($from) {
        var removedAnimations = _.map(this.animations, function (animation) {
            if (!$from
             || $from.filter(animation.el).length
             || $from.find(animation.el).length) {
                animation.destroy();
                return animation;
            }
            return null;
        });
        this.animations = _.difference(this.animations, removedAnimations);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when the root is notified that the animations have to be
     * (re)started.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onAnimationStartDemand: function (ev) {
        this._startAnimations(ev.data.editableMode, ev.data.$target)
            .done(ev.data.onSuccess)
            .fail(ev.data.onFailure);
    },
    /**
     * Called when the root is notified that the animations have to be
     * stopped.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onAnimationStopDemand: function (ev) {
        this._stopAnimations(ev.data.$target);
    },
    /**
     * @todo review
     * @private
     */
    _onLangChangeClick: function (ev) {
        ev.preventDefault();

        var $target = $(ev.target);
        // retrieve the hash before the redirect
        var redirect = {
            lang: $target.data('lang'),
            url: encodeURIComponent($target.attr('href').replace(/[&?]edit_translations[^&?]+/, '')),
            hash: encodeURIComponent(window.location.hash)
        };
        window.location.href = _.str.sprintf("/website/lang/%(lang)s?r=%(url)s%(hash)s", redirect);
    },
    /**
     * Checks information about the page main object.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onMainObjectRequest: function (ev) {
        var repr = $('html').data('main-object');
        var m = repr.match(/(.+)\((\d+),(.*)\)/);
        ev.data.callback({
            model: m[1],
            id: m[2] | 0,
        });
    },
    /**
     * @todo review
     * @private
     */
    _onPublishBtnClick: function (ev) {
        ev.preventDefault();

        var $data = $(ev.currentTarget).parents(".js_publish_management:first");
        this._rpc({
            route: $data.data('controller') || '/website/publish',
            params: {
                id: +$data.data('id'),
                object: $data.data('object'),
            },
        })
        .done(function (result) {
            $data.toggleClass("css_unpublished css_published");
            $data.find('input').prop("checked", result);
            $data.parents("[data-publish]").attr("data-publish", +result ? 'on' : 'off');
        });
    },
    /**
     * @todo review
     * @private
     */
    _onWebsiteFormSubmit: function (ev) {
        var $buttons = $(ev.currentTarget).find('button[type="submit"], a.a-submit');
        _.each($buttons, function (btn) {
            var $btn = $(btn);
            $btn.html('<i class="fa fa-spinner fa-spin"></i> ' + $btn.text());
            $btn.prop('disabled', true);
        });
    },
    /**
     * Called when the root is notified that the button should be
     * disabled after the first click.
     *
     * @private
     * @param {Event} ev
     */
    _onDisableOnClick: function (ev) {
        $(ev.currentTarget).addClass('disabled');
    },

    /**
     * Called when clicking on the multi-website switcher.
     *
     * @param {OdooEvent} ev
     */
    _multiWebsiteSwitch: function (ev) {
        var websiteId = ev.currentTarget.getAttribute('website-id');
        var websiteDomain = ev.currentTarget.getAttribute('domain');
        var url = window.location.href;
        if (websiteDomain && window.location.hostname !== websiteDomain) {
            var path = window.location.pathname + window.location.search + window.location.hash;
            url = websiteDomain + path;
        }
        window.location.href = $.param.querystring(url, {'fw': websiteId});
    },

    _multiCompanySwitch: function (ev) {
        var company_id_to_switch_to = ev.currentTarget.getAttribute('company-id');
        this._rpc({model: 'res.users',
            method: 'write',
            args: [odoo.session_info.user_id, {'company_id': parseInt(company_id_to_switch_to, 10)}],
        }).then(function () {
            window.location.reload(true);
        });
    },
});

return {
    WebsiteRoot: WebsiteRoot,
    websiteRootRegistry: websiteRootRegistry,
};
});
