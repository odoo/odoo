odoo.define('website.editor.link', function (require) {
'use strict';

var weWidgets = require('wysiwyg.widgets');
var wUtils = require('website.utils');
const _t = require('web.core')._t;

weWidgets.LinkTools.include({
    xmlDependencies: (weWidgets.LinkTools.prototype.xmlDependencies || []).concat(
        ['/website/static/src/xml/website.editor.xml']
    ),
    events: _.extend({}, weWidgets.LinkTools.prototype.events || {}, {
        'click we-selection-items[name="link_anchor"] we-button': '_onAnchorChange',
        'click we-selection-items[name="link_action"] we-button': '_onActionChange',
        'input input[name="url"]': '_onURLInput',
        'click .o_we_link_upload_file, .o_we_link_replace_file': '_onLinkUploadFileClick',
        'click .o_we_link_remove_file': '_onLinkRemoveFileClick',
    }),
    custom_events: _.extend({}, weWidgets.LinkTools.prototype.custom_events || {}, {
        website_url_chosen: '_onAutocompleteClose',
    }),
    LINK_DEBOUNCE: 1000,

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._adaptPageAnchor = _.debounce(this._adaptPageAnchor, this.LINK_DEBOUNCE);
        this.fileName = this.$link[0].dataset.fileName;
    },
    /**
     * Allows the URL input to propose existing website pages, or to be filled
     * from document upload
     *
     * @override
     */
    start: async function () {
        var def = await this._super.apply(this, arguments);
        const options = {
            position: {
                collision: 'flip fit',
            },
            classes: {
                "ui-autocomplete": 'o_website_ui_autocomplete'
            },
        };
        this.$urlInput = this.$('input[name="url"]');
        this.$('.o_we_link_action_change').toggle(this.$urlInput.val().includes('/web/'));
        wUtils.autocompleteWithPages(this, this.$urlInput, options);
        this._adaptPageAnchor();
        return def;
    },
    /**
     * @returns {boolean} Whether or not link action is set to download
     */
    isDownloadEnable: function () {
        return this.$link[0].dataset.linkAction === 'download';
    },
    /**
     * If URL starts with /web/ or if the file name is included in URL, then file has been uploaded
     *
     * @returns {boolean} Whether the link points to a file or not
     */
    isFileUploaded: function () {
        let url = this.$urlInput && this.$urlInput.val();
        if (url === undefined) {
            url = this.$link.attr('href');
        }
        let fileName = this.$link[0].dataset.fileName;
        fileName = fileName && fileName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return new RegExp(`${fileName ? fileName + '|' : ''}\\/web\\/`).test(url);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _isNewWindow: function (url) {
        return this.isFileUploaded();
    },
    /**
     * @private
     */
    _adaptPageAnchor: function () {
        const urlInputValue = this.$urlInput.val();
        const $pageAnchor = this.$('.o_link_dialog_page_anchor');
        const isFromWebsite = urlInputValue[0] === '/' && !urlInputValue.startsWith('/web/');
        const $selectMenu = this.$('we-selection-items[name="link_anchor"]');

        if ($selectMenu.data("anchor-for") !== urlInputValue && isFromWebsite) { // avoid useless query
            $pageAnchor.toggleClass('d-none', !isFromWebsite);
            $selectMenu.empty();
            const always = () => $pageAnchor.find('we-toggler').text('\u00A0');
            wUtils.loadAnchors(urlInputValue).then(anchors => {
                for (const anchor of anchors) {
                    const $option = $('<we-button class="dropdown-item">');
                    $option.text(anchor);
                    $option.data('value', anchor);
                    $selectMenu.append($option);
                }
                always();
            }).guardedCatch(always);
        }
        $selectMenu.data("anchor-for", urlInputValue);
    },
    /**
     * Update URL according to chosen action
     *
     * @private
     */
    _adaptURLToAction: function (url) {
        if (this.$link[0].dataset.linkAction !== 'download') {
            url = url.replace(/[&?]+download=true/, '');
        } else if (!/[&?]+download=true/.test(url)) {
            url = url + (url.includes('?') ? '&download=true' : '?download=true');
        }
        return url;
    },
    /**
     * Reset action to default value ie. Open in a new tab
     *
     * @private
     */
    _resetLinkAction: function () {
        this.$('.o_we_link_action_change .active').removeClass('active');
        this.$('.o_we_link_action_change we-button:contains("Open in a new tab")').addClass('active');
        this.$('.o_we_link_action_change we-toggler').text(_t("Open in a new tab"));
        this.$link[0].dataset.fileName = '';
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAutocompleteClose: function () {
        this._onURLInput();
    },
    /**
     * @private
     */
    _onAnchorChange: function () {
        const anchorValue = this.$('[name="link_anchor"] we-button.active').data('value');
        let urlInputValue = this.$urlInput.val();
        if (urlInputValue.indexOf('#') > -1) {
            urlInputValue = urlInputValue.substr(0, urlInputValue.indexOf('#'));
        }
        this.$urlInput.val(urlInputValue + anchorValue);
    },
    /**
     * @override
     */
    _onURLInput: function () {
        const isFileUploaded = this.isFileUploaded();
        const isInternalFile = isFileUploaded && this.$urlInput && this.$urlInput.val().includes('/web/');
        if (isInternalFile) {
            this.$urlInput.val(this._adaptURLToAction(this.$urlInput.val()));
        } else if (this.$urlInput && !isFileUploaded) {
            this._resetLinkAction();
        }
        this.$('.o_we_link_action_change').toggle(isInternalFile);
        this.$('.o_we_link_replace_file').closest('div').toggle(isFileUploaded);
        this.$('.o_we_link_upload_file').toggle(!isFileUploaded);
        this._super.apply(this, arguments);
        this._adaptPageAnchor();
    },
    /**
     * @private
     */
    _onLinkUploadFileClick: function () {
        const documentDialog = new weWidgets.MediaDialog(this, {
            noIcons: true,
            noImages: true,
            noVideos: true,
        });
        documentDialog.on('save', this, function (htmlOutput) {
            const $elem = $(htmlOutput);
            if ($elem.length) {
                const url = $elem.is('a') ? $elem.attr('href') : $elem.attr('src');
                // We need to save the file name in order to display it in the toolbar.
                const file = documentDialog.activeWidget.selectedAttachments[0];
                this.$link[0].dataset.fileName = file.name;
                this.$('.o_we_file_name').text(file.name).attr('title', file.name);
                this.$urlInput.val(url).trigger('input');
            }
        });
        documentDialog.open();
    },
    /**
     * @private
     */
    _onLinkRemoveFileClick: function () {
        this.$link[0].dataset.fileName = "";
        this.$urlInput.val('').trigger('input');
    },
    /**
     * @private
     */
    _onActionChange: function () {
        const actionValue = this.$('[name="link_action"] we-button.active').data('value');
        this.$link[0].dataset.linkAction = actionValue;
        this.$urlInput.trigger('input');
    },
});
});
