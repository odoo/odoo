odoo.define('web_editor.wysiwyg.iframe', function (require) {
'use strict';

var Wysiwyg = require('web_editor.wysiwyg');
var ajax = require('web.ajax');
var core = require('web.core');

var qweb = core.qweb;

var _fnSummernoteMaster = $.fn.summernote;
var _summernoteMaster = $.summernote;
$.fn.summernote = function () {
    var summernote = this[0].ownerDocument.defaultView._fnSummenoteSlave || _fnSummernoteMaster;
    return summernote.apply(this, arguments);
};
window._fnSummernoteMaster = $.fn.summernote;
window._summernoteMaster = _summernoteMaster;

/**
 * Add option (inIframe) to load Wysiwyg in an iframe.
 **/
Wysiwyg.include({
    /**
     * Add options to load Wysiwyg in an iframe.
     *
     * @override
     * @param {boolean} options.inIframe
     **/
    init: function (parent, options) {
        this._super.apply(this, arguments);
        if (this.options.inIframe) {
            if (!this.options.iframeCssAssets) {
                this.options.iframeCssAssets = 'web_editor.wysiwyg_iframe_css_assets';
            }
            this._onUpdateIframeId = 'onLoad_' + this.id;
        }
    },
    /**
     * Load assets to inject into iframe.
     *
     * @override
     **/
    willStart: function () {
        if (!this.options.inIframe) {
            return this._super();
        }
        if (this.options.iframeCssAssets) {
            this.defAsset = ajax.loadAsset(this.options.iframeCssAssets);
        } else {
            this.defAsset = Promise.resolve({cssLibs: [], cssContents: []});
        }
        this.$target = this.$el;
        return this.defAsset
            .then(this._loadIframe.bind(this))
            .then(this._super.bind(this)).then(function () {
                var _summernoteMaster = $.summernote;
                var _summernoteSlave = this.$iframe[0].contentWindow._summernoteSlave;
                _summernoteSlave.options = _.extend({}, _summernoteMaster.options, {modules: _summernoteSlave.options.modules});
                this._enableBootstrapInIframe();
            }.bind(this));
    },
    /**
     * @override
     */
    destroy: function () {
        if (!this.options.inIframe) {
            return this._super();
        }
        $(document.body).off('.' + this.id);

        this.$iframe.parents().removeClass('o_wysiwyg_no_transform');

        this.$target.insertBefore(this.$iframe);

        delete window.top[this._onUpdateIframeId];
        if (this.$iframeTarget) {
            this.$iframeTarget.remove();
        }
        if (this.$iframe) {
            this.$iframe.remove();
        }
        this._super();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Change fullsreen feature.
     *
     * @override
     * @returns {Object} modules list to load
     */
    _getPlugins: function () {
        var self = this;
        var plugins = this._super();
        plugins.fullscreen = plugins.fullscreen.extend({
            toggle: function () {
                if (!self.$iframe) {
                    return this._super();
                }
                self.$iframe.toggleClass('o_fullscreen');
                self.$iframe.contents().find('body').toggleClass('o_fullscreen');

                // Hack to avoid a parent of the fullscreen iframe to have a
                // transform (otherwise the position: fixed won't work)
                self.$iframe.parents().toggleClass('o_wysiwyg_no_transform');
            },
            isFullscreen: function () {
                if (!self.$iframe) {
                    return this._super();
                }
                return self.$iframe.hasClass('o_fullscreen');
            },
        });
        return plugins;
    },
    /**
     * This method is called after the iframe is loaded with the editor. This is
     * to activate the bootstrap features that out of the iframe would launch
     * automatically when changing the dom.
     *
     * @private
     */
    _enableBootstrapInIframe: function () {
        var body = this.$iframe[0].contentWindow.document.body;
        var $toolbarButtons = this._summernote.layoutInfo.toolbar.find('[data-toggle="dropdown"]').dropdown({
            boundary: body,
        });

        function hideDrowpdown() {
            var $expended = $toolbarButtons.filter('[aria-expanded="true"]').parent();
            $expended.children().removeAttr('aria-expanded').removeClass('show');
            $expended.removeClass('show');
        }
        $(body).on('mouseup.' + this.id, hideDrowpdown);
        $(document.body).on('click.' + this.id, hideDrowpdown);
    },
    /**
     * Create iframe, inject css and create a link with the content,
     * then inject the target inside.
     *
     * @private
     * @returns {Promise}
     */
    _loadIframe: function () {
        var self = this;
        this.$iframe = $('<iframe class="wysiwyg_iframe">').css({
            'min-height': '400px',
            width: '100%'
        });
        var avoidDoubleLoad = 0; // this bug only appears on some configurations.

        // resolve deferred on load
        var def = new Promise(function (resolve) {
            window.top[self._onUpdateIframeId] = function (_avoidDoubleLoad) {
                if (_avoidDoubleLoad !== avoidDoubleLoad) {
                    console.warn('Wysiwyg iframe double load detected');
                    return;
                }
                delete window.top[self._onUpdateIframeId];
                var $iframeTarget = self.$iframe.contents().find('#iframe_target');
                $iframeTarget.append(self.$target);
                resolve();
            };
        });
        this.$iframe.data('loadDef', def);  // for unit test

        // inject content in iframe

        this.$iframe.on('load', function onLoad (ev) {
            var _avoidDoubleLoad = ++avoidDoubleLoad;
            this.defAsset.then(function (asset) {
                if (_avoidDoubleLoad !== avoidDoubleLoad) {
                    console.warn('Wysiwyg immediate iframe double load detected');
                    return;
                }
                var iframeContent = qweb.render('wysiwyg.iframeContent', {
                    asset: asset,
                    updateIframeId: this._onUpdateIframeId,
                    avoidDoubleLoad: _avoidDoubleLoad
                });
                this.$iframe[0].contentWindow.document
                    .open("text/html", "replace")
                    .write(iframeContent);
            }.bind(this));
        }.bind(this));

        this.$iframe.insertAfter(this.$target);

        return def;
    },
});

//--------------------------------------------------------------------------
// Public helper
//--------------------------------------------------------------------------

/**
 * Get the current range from Summernote.
 *
 * @param {Node} [DOM]
 * @returns {Object}
*/
Wysiwyg.getRange = function (DOM) {
    var summernote = (DOM.defaultView || DOM.ownerDocument.defaultView)._summernoteSlave || _summernoteMaster;
    var range = summernote.range.create();
    return range && {
        sc: range.sc,
        so: range.so,
        ec: range.ec,
        eo: range.eo,
    };
};
/**
 * @param {Node} sc - start container
 * @param {Number} so - start offset
 * @param {Node} ec - end container
 * @param {Number} eo - end offset
*/
Wysiwyg.setRange = function (sc, so, ec, eo) {
    var summernote = sc.ownerDocument.defaultView._summernoteSlave || _summernoteMaster;
    $(sc).focus();
    if (ec) {
        summernote.range.create(sc, so, ec, eo).select();
    } else {
        summernote.range.create(sc, so).select();
    }
    // trigger for Unbreakable
    $(sc.tagName ? sc : sc.parentNode).trigger('wysiwyg.range');
};

});
