odoo.define('wysiwyg.widgets.media', function (require) {
'use strict';

var core = require('web.core');
var fonts = require('wysiwyg.fonts');
var utils = require('web.utils');
var Widget = require('web.Widget');
const {removeOnImageChangeAttrs} = require('web_editor.image_processing');
const {getCSSVariableValue, DEFAULT_PALETTE} = require('web_editor.utils');

var QWeb = core.qweb;
var _t = core._t;

var MediaWidget = Widget.extend({
    xmlDependencies: ['/web_editor/static/src/xml/wysiwyg.xml'],
});

var SearchableMediaWidget = MediaWidget.extend({});

/**
 * Let users choose a file, including uploading a new file in odoo.
 */
var FileWidget = SearchableMediaWidget.extend({
    /**
     * @private
     * @returns {Promise}
     */
    _save: async function () {
        const selected = this.selectedAttachments;

        const img = selected[0];
        if (!img || !img.id || this.$media.attr('src') === img.image_src) {
            return this.media;
        }

        this.$media.attr('alt', img.alt || img.description || '');
        var style = this.style;
        if (style) {
            this.$media.css(style);
        }

        this.media.classList.remove('o_modified_image_to_save');
        this.$media.trigger('image_changed');
        return this.media;
    },
});

/**
 * Let users choose an image, including uploading a new image in odoo.
 */
var ImageWidget = FileWidget.extend({});


/**
 * Let users choose a document, including uploading a new document in odoo.
 */
var DocumentWidget = FileWidget.extend({});

/**
 * Let users choose a font awesome icon, support all font awesome loaded in the
 * css files.
 */
var IconWidget = SearchableMediaWidget.extend({
    save: function () {
        var style = this.$media.attr('style') || '';
        var iconFont = this._getFont(this.selectedIcon) || {base: 'fa', font: ''};
        if (!this.$media.is('span, i')) {
            var $span = $('<span/>');
            $span.data(this.$media.data());
            this.$media = $span;
            this.media = this.$media[0];
            style = style.replace(/\s*width:[^;]+/, '');
        }
        this.$media.removeClass(this.initialIcon).addClass([iconFont.base, iconFont.font]);
        this.$media.attr('style', style || null);
        return Promise.resolve(this.media);
    },
    _getFont: function (classNames) {
        if (!(classNames instanceof Array)) {
            classNames = (classNames || "").split(/\s+/);
        }
        var fontIcon, cssData;
        for (var k = 0; k < this.iconsParser.length; k++) {
            fontIcon = this.iconsParser[k];
            for (var s = 0; s < fontIcon.cssData.length; s++) {
                cssData = fontIcon.cssData[s];
                if (_.intersection(classNames, cssData.names).length) {
                    return {
                        base: fontIcon.base,
                        parser: fontIcon.parser,
                        font: cssData.names[0],
                    };
                }
            }
        }
        return null;
    },
});

/**
 * Let users choose a video, support embed iframe.
 */
var VideoWidget = MediaWidget.extend({
    save: async function () {
        await this._updateVideo();
        const videoSrc = this.$content.attr('src');
        if (this.isForBgVideo) {
            return Promise.resolve({bgVideoSrc: videoSrc});
        }
        if (this.$('.o_video_dialog_iframe').is('iframe') && videoSrc) {
            this.$media = this.getWrappedIframe(videoSrc);
            this.media = this.$media[0];
        }
        return Promise.resolve(this.media);
    },

    /**
     * Get an iframe wrapped for the website builder.
     *
     * @param {string} src The video url.
     */
    getWrappedIframe: function (src) {
        return $(
            '<div class="media_iframe_video" data-oe-expression="' + src + '">' +
                '<div class="css_editable_mode_display">&nbsp;</div>' +
                '<div class="media_iframe_video_size" contenteditable="false">&nbsp;</div>' +
                '<iframe src="' + src + '" frameborder="0" contenteditable="false" allowfullscreen="allowfullscreen"></iframe>' +
            '</div>'
        );
    },
    /**
     * Creates a video node according to the given URL and options. If not
     * possible, returns an error code.
     *
     * @param {string} url
     * @param {Object} options
     * @returns {Object}
     *          $video -> the created video jQuery node
     *          type -> the type of the created video
     *          errorCode -> if defined, either '0' for invalid URL or '1' for
     *              unsupported video provider
     */
    createVideoNode: async function (url, options) {
        options = options || {};
        const videoData = await this._getVideoURLData(url, options);
        if (videoData.error) {
            return {errorCode: 0};
        }
        if (!videoData.platform) {
            return {errorCode: 1};
        }
        const $video = $('<iframe>').width(1280).height(720)
            .attr('frameborder', 0)
            .attr('src', videoData.embed_url)
            .addClass('o_video_dialog_iframe');

        return {$video: $video, platform: videoData.platform};
    },
});

return {
    MediaWidget: MediaWidget,
    SearchableMediaWidget: SearchableMediaWidget,
    FileWidget: FileWidget,
    ImageWidget: ImageWidget,
    DocumentWidget: DocumentWidget,
    IconWidget: IconWidget,
    VideoWidget: VideoWidget,
};
});
