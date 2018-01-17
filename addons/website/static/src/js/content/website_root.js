odoo.define('website.WebsiteRoot.instance', function (require) {
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
    }),
    custom_events: _.extend({}, BodyManager.prototype.custom_events || {}, {
        animation_start_demand: '_onAnimationStartDemand',
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
        var defs = _.map(sAnimation.registry, function (Animation) {
            var selector = Animation.prototype.selector || '';
            var $target = $from.find(selector).addBack(selector);

            var defs = _.map($target, function (el) {
                var $snippet = $(el);
                var animation = $snippet.data('snippet-view');
                if (animation) {
                    self.animations = _.without(self.animations, animation);
                    animation.destroy();
                }
                animation = new Animation(self, editableMode);
                self.animations.push(animation);
                $snippet.data('snippet-view', animation);
                return animation.attachTo($snippet);
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
     */
    _stopAnimations: function () {
        _.each(this.animations, function (animation) {
            animation.destroy();
        });
        this.animations = [];
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
     */
    _onAnimationStopDemand: function () {
        this._stopAnimations();
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
     * @todo review
     * @private
     */
    _onPublishBtnClick: function (ev) {
        ev.preventDefault();

        var self = this;
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
        })
        .fail(function (err, data) {
            return new Dialog(self, {
                title: data.data ? data.data.arguments[0] : "",
                $content: $('<div/>', {
                    html: (data.data ? data.data.arguments[1] : data.statusText)
                        + '<br/>'
                        + _.str.sprintf(
                            _t('It might be possible to edit the relevant items or fix the issue in <a href="%s">the classic Odoo interface</a>'),
                            '/web#return_label=Website&model=' + $data.data('object') + '&id=' + $data.data('id')
                        ),
                }),
            }).open();
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
            $btn.attr('data-loading-text', '<i class="fa fa-spinner fa-spin"></i> ' + $(btn).text());
            $btn.button('loading');
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
});

return {
    WebsiteRoot: WebsiteRoot,
    websiteRootRegistry: websiteRootRegistry,
};
});
