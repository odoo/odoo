odoo.define('web_editor.wysiwyg.iframe', function (require) {
'use strict';

var Wysiwyg = require('web_editor.wysiwyg');
var ajax = require('web.ajax');
var core = require('web.core');
var config = require('web.config');

var qweb = core.qweb;
var promiseCommon;
var promiseWysiwyg;


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
            this._onUpdateIframeId = 'onLoad_' + this.id;
        }
        this.__extraAssetsForIframe = [];
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

        var defAsset;
        if (this.options.iframeCssAssets) {
            defAsset = ajax.loadAsset(this.options.iframeCssAssets);
        } else {
            defAsset = Promise.resolve({
                cssLibs: [],
                cssContents: []
            });
        }

        promiseWysiwyg = promiseWysiwyg || ajax.loadAsset('web_editor.wysiwyg_iframe_editor_assets');
        this.defAsset = Promise.all([promiseWysiwyg, defAsset]);

        this.$target = this.$el;
        return this.defAsset
            .then(this._loadIframe.bind(this))
            .then(this._super.bind(this));
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
            'min-height': '55vh',
            width: '100%'
        });
        var avoidDoubleLoad = 0; // this bug only appears on some configurations.

        // resolve promise on load
        var def = new Promise(function (resolve) {
            window.top[self._onUpdateIframeId] = function (Editor, _avoidDoubleLoad) {
                if (_avoidDoubleLoad !== avoidDoubleLoad) {
                    console.warn('Wysiwyg iframe double load detected');
                    return;
                }
                delete window.top[self._onUpdateIframeId];
                var $iframeTarget = self.$iframe.contents().find('#iframe_target');
                $iframeTarget.attr("isMobile", config.device.isMobile);
                $iframeTarget.find('.o_editable').html(self.$target.val());
                self.options.toolbarHandler = $('#web_editor-top-edit', self.$iframe[0].contentWindow.document);
                $(qweb.render('web_editor.FieldTextHtml.fullscreen'))
                    .appendTo(self.options.toolbarHandler)
                    .on('click', '.o_fullscreen', function () {
                        $("body").toggleClass("o_field_widgetTextHtml_fullscreen");
                        var full = $("body").hasClass("o_field_widgetTextHtml_fullscreen");
                        self.$iframe.parents().toggleClass('o_form_fullscreen_ancestor', full);
                        $(window).trigger("resize"); // induce a resize() call and let other backend elements know (the navbar extra items management relies on this)
                    });
                self.Editor = Editor;
                resolve();
            };
        });
        this.$iframe.data('loadDef', def); // for unit test

        // inject content in iframe

        this.$iframe.on('load', function onLoad (ev) {
            var _avoidDoubleLoad = ++avoidDoubleLoad;
            self.defAsset.then(function (assets) {
                if (_avoidDoubleLoad !== avoidDoubleLoad) {
                    console.warn('Wysiwyg immediate iframe double load detected');
                    return;
                }

                var iframeContent = qweb.render('wysiwyg.iframeContent', {
                    assets: assets.concat(self.__extraAssetsForIframe),
                    updateIframeId: self._onUpdateIframeId,
                    avoidDoubleLoad: _avoidDoubleLoad
                });
                self.$iframe[0].contentWindow.document
                    .open("text/html", "replace")
                    .write(iframeContent);
            });
        });

        this.$iframe.insertAfter(this.$target);

        return def;
    },
});

});
