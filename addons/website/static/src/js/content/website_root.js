odoo.define('website.root', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
const KeyboardNavigationMixin = require('web.KeyboardNavigationMixin');
const session = require('web.session');
var publicRootData = require('web.public.root');
require("web.zoomodoo");

var _t = core._t;

var websiteRootRegistry = publicRootData.publicRootRegistry;

var WebsiteRoot = publicRootData.PublicRoot.extend(KeyboardNavigationMixin, {
    events: _.extend({}, KeyboardNavigationMixin.events, publicRootData.PublicRoot.prototype.events || {}, {
        'click .js_change_lang': '_onLangChangeClick',
        'click .js_publish_management .js_publish_btn': '_onPublishBtnClick',
        'click .js_multi_website_switch': '_onWebsiteSwitch',
        'shown.bs.modal': '_onModalShown',
    }),
    custom_events: _.extend({}, publicRootData.PublicRoot.prototype.custom_events || {}, {
        'ready_to_clean_for_save': '_onWidgetsStopRequest',
        seo_object_request: '_onSeoObjectRequest',
    }),

    /**
     * @override
     */
    init() {
        this.isFullscreen = false;
        KeyboardNavigationMixin.init.call(this, {
            autoAccessKeys: false,
        });
        return this._super(...arguments);
    },
    /**
     * @override
     */
    start: function () {
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

        // Enable magnify on zommable img
        this.$('.zoomable img[data-zoom]').zoomOdoo();

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getContext: function (context) {
        var html = document.documentElement;
        return _.extend({
            'website_id': html.getAttribute('data-website-id') | 0,
        }, this._super.apply(this, arguments));
    },
    /**
     * @override
     */
    _getExtraContext: function (context) {
        var html = document.documentElement;
        return _.extend({
            'editable': !!(html.dataset.editable || $('[data-oe-model]').length), // temporary hack, this should be done in python
            'translatable': !!html.dataset.translatable,
            'edit_translations': !!html.dataset.edit_translations,
        }, this._super.apply(this, arguments));
    },
    /**
     * @override
     */
    _getPublicWidgetsRegistry: function (options) {
        var registry = this._super.apply(this, arguments);
        if (options.editableMode) {
            return _.pick(registry, function (PublicWidget) {
                return !PublicWidget.prototype.disabledInEditableMode;
            });
        }
        return registry;
    },
    /**
     * Toggles the fullscreen mode.
     *
     * @private
     * @param {boolean} state toggle fullscreen on/off (true/false)
     */
    _toggleFullscreen(state) {
        this.isFullscreen = state;
        document.body.classList.toggle('o_fullscreen', this.isFullscreen);
        document.body.style.overflowX = 'hidden';
        let resizing = true;
        window.requestAnimationFrame(function resizeFunction() {
            window.dispatchEvent(new Event('resize'));
            if (resizing) {
                window.requestAnimationFrame(resizeFunction);
            }
        });
        let stopResizing;
        const onTransitionEnd = ev => {
            if (ev.target === document.body && ev.propertyName === 'padding-top') {
                stopResizing();
            }
        };
        stopResizing = () => {
            resizing = false;
            document.body.style.overflowX = '';
            document.body.removeEventListener('transitionend', onTransitionEnd);
        };
        document.body.addEventListener('transitionend', onTransitionEnd);
        // Safeguard in case the transitionend event doesn't trigger for whatever reason.
        window.setTimeout(() => stopResizing(), 500);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _onWidgetsStartRequest: function (ev) {
        ev.data.options = _.clone(ev.data.options || {});
        ev.data.options.editableMode = ev.data.editableMode;
        this._super.apply(this, arguments);
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
            lang: $target.data('url_code'),
            url: encodeURIComponent($target.attr('href').replace(/[&?]edit_translations[^&?]+/, '')),
            hash: encodeURIComponent(window.location.hash)
        };
        window.location.href = _.str.sprintf("/website/lang/%(lang)s?r=%(url)s%(hash)s", redirect);
    },
    /**
    /**
     * Checks information about the page SEO object.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSeoObjectRequest: function (ev) {
        var res = this._unslugHtmlDataObject('seo-object');
        ev.data.callback(res);
    },
    /**
     * Returns a model/id object constructed from html data attribute.
     *
     * @private
     * @param {string} dataAttr
     * @returns {Object} an object with 2 keys: model and id, or null
     * if not found
     */
    _unslugHtmlDataObject: function (dataAttr) {
        var repr = $('html').data(dataAttr);
        var match = repr && repr.match(/(.+)\((\d+),(.*)\)/);
        if (!match) {
            return null;
        }
        return {
            model: match[1],
            id: match[2] | 0,
        };
    },
    /**
     * @todo review
     * @private
     */
    _onPublishBtnClick: function (ev) {
        ev.preventDefault();
        if (document.body.classList.contains('editor_enable')) {
            return;
        }

        var self = this;
        var $data = $(ev.currentTarget).parents(".js_publish_management:first");
        this._rpc({
            route: $data.data('controller') || '/website/publish',
            params: {
                id: +$data.data('id'),
                object: $data.data('object'),
            },
        })
        .then(function (result) {
            $data.toggleClass("css_unpublished css_published");
            $data.find('input').prop("checked", result);
            $data.parents("[data-publish]").attr("data-publish", +result ? 'on' : 'off');
            if (result) {
                self.displayNotification({
                    type: 'success',
                    title: _t("Congratulations"),
                    message: $data.data('description') ?
                        _.str.sprintf(_t("You've published your %s."), $data.data('description')) :
                        _t("Published with success."),
                });
            }
        })
        .guardedCatch(function (err, data) {
            data = data || {statusText: err.message.message};
            return new Dialog(self, {
                title: data.data ? data.data.arguments[0] : "",
                $content: $('<div/>', {
                    html: (data.data ? data.data.arguments[1] : data.statusText)
                        + '<br/>'
                        + _.str.sprintf(
                            _t('It might be possible to edit the relevant items or fix the issue in <a href="%s">the classic Odoo interface</a>'),
                            '/web#model=' + $data.data('object') + '&id=' + $data.data('id')
                        ),
                }),
            }).open();
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onWebsiteSwitch: function (ev) {
        var websiteId = ev.currentTarget.getAttribute('website-id');
        var websiteDomain = ev.currentTarget.getAttribute('domain');
        var url = window.location.href;
        if (websiteDomain && window.location.hostname !== websiteDomain) {
            var path = window.location.pathname + window.location.search + window.location.hash;
            url = websiteDomain + path;
        }
        window.location.href = $.param.querystring(url, {'fw': websiteId});
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onModalShown: function (ev) {
        $(ev.target).addClass('modal_shown');
    },
    /**
     * @override
     */
    _onKeyDown(ev) {
        if (!session.user_id) {
            return;
        }
        // If document.body doesn't contain the element, it was probably removed as a consequence of pressing Esc.
        // we don't want to toggle fullscreen as the removal (eg, closing a modal) is the intended action.
        if (ev.keyCode !== $.ui.keyCode.ESCAPE || !document.body.contains(ev.target) || ev.target.closest('.modal')) {
            return KeyboardNavigationMixin._onKeyDown.apply(this, arguments);
        }
        this._toggleFullscreen(!this.isFullscreen);
    },
});

return {
    WebsiteRoot: WebsiteRoot,
    websiteRootRegistry: websiteRootRegistry,
};
});
