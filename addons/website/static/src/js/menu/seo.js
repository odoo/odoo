odoo.define('website.seo', function (require) {
'use strict';

var core = require('web.core');
var Class = require('web.Class');
var Dialog = require('web.Dialog');
var mixins = require('web.mixins');
var rpc = require('web.rpc');
var Widget = require('web.Widget');
var weContext = require('web_editor.context');
var weWidgets = require('web_editor.widget');
var websiteNavbarData = require('website.navbar');

var _t = core._t;

// This replaces \b, because accents(e.g. à, é) are not seen as word boundaries.
// Javascript \b is not unicode aware, and words beginning or ending by accents won't match \b
var WORD_SEPARATORS_REGEX = '([\\u2000-\\u206F\\u2E00-\\u2E7F\'!"#\\$%&\\(\\)\\*\\+,\\-\\.\\/:;<=>\\?¿¡@\\[\\]\\^_`\\{\\|\\}~\\s]+|^|$)';

var Suggestion = Widget.extend({
    template: 'website.seo_suggestion',
    xmlDependencies: ['/website/static/src/xml/website.seo.xml'],
    events: {
        'click .js_seo_suggestion': 'select',
    },

    init: function (parent, options) {
        this.keyword = options.keyword;
        this._super(parent);
    },
    select: function () {
        this.trigger('selected', this.keyword);
    },
});

var SuggestionList = Widget.extend({
    template: 'website.seo_suggestion_list',
    xmlDependencies: ['/website/static/src/xml/website.seo.xml'],

    init: function (parent, options) {
        this.root = options.root;
        this.language = options.language;
        this.htmlPage = options.htmlPage;
        this._super(parent);
    },
    start: function () {
        this.refresh();
    },
    refresh: function () {
        var self = this;
        self.$el.append(_t("Loading..."));
        var language = self.language || weContext.get().lang.toLowerCase();
        this._rpc({
            route: '/website/seo_suggest',
            params: {
                keywords: self.root,
                lang: language,
            },
        }).then(function (keyword_list) {
            self.addSuggestions(JSON.parse(keyword_list));
        });
    },
    addSuggestions: function (keywords) {
        var self = this;
        self.$el.empty();
        // TODO Improve algorithm + Ajust based on custom user keywords
        var regex = new RegExp(WORD_SEPARATORS_REGEX + self.root + WORD_SEPARATORS_REGEX, 'gi');
        keywords = _.map(_.uniq(keywords), function (word) {
            return word.replace(regex, '').trim();
        });
        // TODO Order properly ?
        _.each(keywords, function (keyword) {
            if (keyword) {
                var suggestion = new Suggestion(self, {
                    keyword: keyword,
                });
                suggestion.on('selected', self, function (word, language) {
                    self.trigger('selected', word, language);
                });
                suggestion.appendTo(self.$el);
            }
        });
     },
});

var Keyword = Widget.extend({
    template: 'website.seo_keyword',
    xmlDependencies: ['/website/static/src/xml/website.seo.xml'],
    events: {
        'click a[data-action=remove-keyword]': 'destroy',
    },

    init: function (parent, options) {
        this.keyword = options.word;
        this.language = options.language;
        this.htmlPage = options.htmlPage;
        this.used_h1 = this.htmlPage.isInHeading1(this.keyword);
        this.used_h2 = this.htmlPage.isInHeading2(this.keyword);
        this.used_content = this.htmlPage.isInBody(this.keyword);
        this._super(parent);
    },
    start: function () {
        this.$('.js_seo_keyword_suggestion').empty();
        this.suggestionList = new SuggestionList(this, {
            root: this.keyword,
            language: this.language,
            htmlPage: this.htmlPage,
        });
        this.suggestionList.on('selected', this, function (word, language) {
            this.trigger('selected', word, language);
        });
        this.suggestionList.appendTo(this.$('.js_seo_keyword_suggestion'));

        this.htmlPage.on('title-changed', this, this._updateTitle);
        this.htmlPage.on('description-changed', this, this._updateDescription);
        this._updateTitle();
        this._updateDescription();
    },
    destroy: function () {
        this.trigger('removed');
        this._super();
    },
    _updateTitle: function () {
        var $title = this.$('.js_seo_keyword_title');
        if (this.htmlPage.isInTitle(this.keyword)) {
            $title.css('visibility','visible');
        } else {
            $title.css('visibility','hidden');
        }
    },
    _updateDescription: function () {
        var $description = this.$('.js_seo_keyword_description');
        if (this.htmlPage.isInDescription(this.keyword)) {
            $description.css('visibility','visible');
        } else {
            $description.css('visibility','hidden');
        }
    },
});

var KeywordList = Widget.extend({
    template: 'website.seo_list',
    xmlDependencies: ['/website/static/src/xml/website.seo.xml'],
    maxKeywords: 10,

    init: function (parent, options) {
        this.htmlPage = options.htmlPage;
        this._super(parent);
    },
    start: function () {
        var self = this;
        var existingKeywords = self.htmlPage.keywords();
        if (existingKeywords.length > 0) {
            _.each(existingKeywords, function (word) {
                self.add.call(self, word);
            });
        }
    },
    keywords: function () {
        var result = [];
        this.$('.js_seo_keyword').each(function () {
            result.push($(this).data('keyword'));
        });
        return result;
    },
    isFull: function () {
        return this.keywords().length >= this.maxKeywords;
    },
    exists: function (word) {
        return _.contains(this.keywords(), word);
    },
    add: function (candidate, language) {
        var self = this;
        // TODO Refine
        var word = candidate ? candidate.replace(/[,;.:<>]+/g, ' ').replace(/ +/g, ' ').trim().toLowerCase() : '';
        if (word && !self.isFull() && !self.exists(word)) {
            var keyword = new Keyword(self, {
                word: word,
                language: language,
                htmlPage: this.htmlPage,
            });
            keyword.on('removed', self, function () {
               self.trigger('list-not-full');
               self.trigger('content-updated', true);
            });
            keyword.on('selected', self, function (word, language) {
                self.trigger('selected', word, language);
            });
            keyword.appendTo(self.$el);
        }
        if (self.isFull()) {
            self.trigger('list-full');
        }
        self.trigger('content-updated');
    },
});

var Preview = Widget.extend({
    template: 'website.seo_preview',
    xmlDependencies: ['/website/static/src/xml/website.seo.xml'],

    init: function (parent, options) {
        this.title = options.title;
        this.url = options.url;
        this.description = options.description || _t("The description will be generated by search engines based on page content unless you specify one.");
        if (this.description.length > 160) {
            this.description = this.description.substring(0,159) + '…';
        }
        this._super(parent);
    },
});

var HtmlPage = Class.extend(mixins.PropertiesMixin, {
    init: function () {
        mixins.PropertiesMixin.init.call(this);
        this.initTitle = this.title();
        this.initDescription = this.description();
    },
    url: function () {
        return window.location.origin + window.location.pathname;
    },
    title: function () {
        return $('title').text().trim();
    },
    changeTitle: function (title) {
        // TODO create tag if missing
        $('title').text(title.trim() || this.initTitle);
        this.trigger('title-changed', title);
    },
    description: function () {
        return ($('meta[name=description]').attr('content') || '').trim();
    },
    changeDescription: function (description) {
        // TODO create tag if missing
        $('meta[name=description]').attr('content', description);
        this.trigger('description-changed', description);
    },
    keywords: function () {
        var $keywords = $('meta[name=keywords]');
        var parsed = ($keywords.length > 0) && $keywords.attr('content') && $keywords.attr('content').split(',');
        return (parsed && parsed[0]) ? parsed: [];
    },
    changeKeywords: function (keywords) {
        // TODO create tag if missing
        $('meta[name=keywords]').attr('content', keywords.join(','));
    },
    headers: function (tag) {
        return $('#wrap '+tag).map(function () {
            return $(this).text();
        });
    },
    getOgMeta: function () {
        var ogImageUrl = $('meta[property="og:image"]').attr('content');
        var title = $('meta[property="og:title"]').attr('content');
        var description = $('meta[property="og:description"]').attr('content');
        return {
            ogImageUrl: ogImageUrl && ogImageUrl.replace(window.location.origin, ''),
            metaTitle: title,
            metaDescription: description,
        };
    },
    images: function () {
        return $('#wrap img').map(function () {
            var $img = $(this);
            return  {
                src: $img.attr('src'),
                alt: $img.attr('alt'),
            };
        });
    },
    company: function () {
        return $('html').attr('data-oe-company-name');
    },
    bodyText: function () {
        return $('body').children().not('.oe_seo_configuration').text();
    },
    heading1: function () {
        return $('body').children().not('.oe_seo_configuration').find('h1').text();
    },
    heading2: function () {
        return $('body').children().not('.oe_seo_configuration').find('h2').text();
    },
    isInBody: function (text) {
        return new RegExp(WORD_SEPARATORS_REGEX+text+WORD_SEPARATORS_REGEX, 'gi').test(this.bodyText());
    },
    isInTitle: function (text) {
        return new RegExp(WORD_SEPARATORS_REGEX+text+WORD_SEPARATORS_REGEX, 'gi').test(this.title());
    },
    isInDescription: function (text) {
        return new RegExp(WORD_SEPARATORS_REGEX+text+WORD_SEPARATORS_REGEX, 'gi').test(this.description());
    },
    isInHeading1: function (text) {
        return new RegExp(WORD_SEPARATORS_REGEX+text+WORD_SEPARATORS_REGEX, 'gi').test(this.heading1());
    },
    isInHeading2: function (text) {
        return new RegExp(WORD_SEPARATORS_REGEX+text+WORD_SEPARATORS_REGEX, 'gi').test(this.heading2());
    },
});

var MetaTitleDescription = Widget.extend({
    // Form and preview for SEO meta title and meta description
    //
    // We only want to show an alert for "description too small" on those cases
    // - at init and the description is not empty
    // - we reached past the minimum and went back to it
    // - focus out of the field
    // Basically we don't want the too small alert when the field is empty and
    // we start typing on it.
    template: 'website.seo_meta_title_description',
    xmlDependencies: ['/website/static/src/xml/website.seo.xml'],
    events: {
        'input input[name=website_meta_title]': '_titleChanged',
        'input textarea[name=website_meta_description]': '_descriptionOnInput',
        'change textarea[name=website_meta_description]': '_descriptionOnChange',
    },
    maxRecommendedDescriptionSize: 300,
    minRecommendedDescriptionSize: 50,
    showDescriptionTooSmall: false,

    /**
     * @override
     */
    init: function (parent, options) {
        this.htmlPage = options.htmlPage;
        this.canEditTitle = !!options.canEditTitle;
        this.canEditDescription = !!options.canEditDescription;
        this.isIndexed = !!options.isIndexed;
        this._super(parent, options);
    },
    /**
     * @override
     */
    start: function () {
        this.$title = this.$('input[name=website_meta_title]');
        this.$description = this.$('textarea[name=website_meta_description]');
        this.$warning = this.$('div#website_meta_description_warning');
        this.$preview = this.$('.js_seo_preview');

        this._renderPreview();

        if (!this.canEditTitle) {
            this.$title.attr('disabled', true);
        }
        if (!this.canEditDescription) {
            this.$description.attr('disabled', true);
        }

        this.$title.val(this.htmlPage.title());
        this.$description.val(this.htmlPage.description());

        this._descriptionOnChange();
    },
    /**
     * Get the current title
     */
    getTitle: function () {
        return this.$title.val().trim() || this.htmlPage.initTitle;
    },
    /**
     * Get the current description
     */
    getDescription: function () {
        return this.$description.val();
    },
    /**
     * @private
     */
    _titleChanged: function () {
        var self = this;
        self._renderPreview();
        self.trigger('title-changed');
    },
    /**
     * @private
     */
    _descriptionOnChange: function () {
        this.showDescriptionTooSmall = true;
        this._descriptionOnInput();
    },
    /**
     * @private
     */
    _descriptionOnInput: function () {
        var length = this.getDescription().length;

        if (length >= this.minRecommendedDescriptionSize) {
            this.showDescriptionTooSmall = true;
        } else if (length === 0) {
            this.showDescriptionTooSmall = false;
        }

        if (length > this.maxRecommendedDescriptionSize) {
            this.$warning.text(_t('Your description looks too long.')).show();
        } else if (this.showDescriptionTooSmall && length < this.minRecommendedDescriptionSize) {
            this.$warning.text(_t('Your description looks too short.')).show();
        } else {
            this.$warning.hide();
        }

        this._renderPreview();
        this.trigger('description-changed');
    },
    /**
     * @private
     */
    _renderPreview: function () {
        var indexed = this.isIndexed;
        var preview = "";
        if (indexed){
            preview = new Preview(this, {
                title: this.getTitle(),
                description: this.getDescription(),
                url: this.htmlPage.url(),
            });
        } else {
            preview = new Preview(this, {
                description: _t("You have hidden this page from search results. It won't be indexed by search engines."),
            });
        }
        this.$preview.empty();
        preview.appendTo(this.$preview);
    },
});

var MetaKeywords = Widget.extend({
    // Form and table for SEO meta keywords
    template: 'website.seo_meta_keywords',
    xmlDependencies: ['/website/static/src/xml/website.seo.xml'],
    events: {
        'keyup input[name=website_meta_keywords]': '_confirmKeyword',
        'click button[data-action=add]': '_addKeyword',
    },

    init: function (parent, options) {
        this.htmlPage = options.htmlPage;
        this._super(parent, options);
    },
    start: function () {
        var self = this;
        this.$input = this.$('input[name=website_meta_keywords]');
        this.keywordList = new KeywordList(this, { htmlPage: this.htmlPage });
        this.keywordList.on('list-full', this, function () {
            self.$input.attr({
                readonly: 'readonly',
                placeholder: "Remove a keyword first"
            });
            self.$('button[data-action=add]').prop('disabled', true).addClass('disabled');
        });
        this.keywordList.on('list-not-full', this, function () {
            self.$input.removeAttr('readonly').attr('placeholder', "");
            self.$('button[data-action=add]').prop('disabled', false).removeClass('disabled');
        });
        this.keywordList.on('selected', this, function (word, language) {
            self.keywordList.add(word, language);
        });
        this.keywordList.on('content-updated', this, function (removed) {
            self._updateTable(removed);
        });
        this.keywordList.insertAfter(this.$('.table thead'));

        this._getLanguages();
        this._updateTable();
    },
    _addKeyword: function () {
        var $language = this.$('select[name=seo_page_language]');
        var keyword = this.$input.val();
        var language = $language.val().toLowerCase();
        this.keywordList.add(keyword, language);
        this.$input.val('').focus();
    },
    _confirmKeyword: function (e) {
        if (e.keyCode === 13) {
            this._addKeyword();
        }
    },
    _getLanguages: function () {
        var self = this;
        this._rpc({
            model: 'website',
            method: 'get_languages',
            args: [[weContext.get().website_id]],
        }).then( function (data) {
            self.$('#language-box').html(core.qweb.render('Configurator.language_promote', {
                'language': data,
                'def_lang': weContext.get().lang
            }));
        });
    },
    /*
     * Show the table if there is at least one keyword. Hide it otherwise.
     *
     * @private
     * @param {boolean} removed: a keyword is about to be removed,
     *   we need to exclude it from the count
     */
    _updateTable : function (removed) {
        var min = removed ? 1 : 0;
        if (this.keywordList.keywords().length > min) {
            this.$('table').show();
        } else {
            this.$('table').hide();
        }
    },
});

var MetaImageSelector = Widget.extend({
    template: 'website.seo_meta_image_selector',
    xmlDependencies: ['/website/static/src/xml/website.seo.xml'],
    events: {
        'click .o_meta_img_upload': '_onClickUploadImg',
        'click .o_meta_img': '_onClickSelectImg',
    },
    /**
     * @override
     * @param {widget} parent
     * @param {Object} data
     */
    init: function (parent, data) {
        this.metaTitle = data.title || '';
        this._setDescription(data.description);
        this.activeMetaImg = data.metaImg;
        this.serverUrl = data.htmlpage.url();
        data.pageImages.unshift(_.str.sprintf('/web/image/res.company/%s/logo', odoo.session_info.website_company_id));
        data.pageImages.unshift(_.str.sprintf('/web/image/website/%s/social_default_image', odoo.session_info.website_id));
        this.images = _.uniq(data.pageImages);
        this.customImgUrl = _.contains(data.pageImages, data.metaImg) ? false : data.metaImg;
        this._super(parent);
    },
    setTitle: function (title) {
        this.metaTitle = title;
        this._updateTemplateBody();
    },
    setDescription: function (description) {
        this._setDescription(description);
        this._updateTemplateBody();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Set the description, applying ellipsis if too long.
     *
     * @private
    */
    _setDescription: function (description) {
        this.metaDescription = description || _t("The description will be generated by social media based on page content unless you specify one.");
        if (this.metaDescription.length > 160) {
            this.metaDescription = this.metaDescription.substring(0,159) + '…';
        }
    },

    /**
     * Update template.
     *
     * @private
    */
    _updateTemplateBody: function () {
        this.$el.empty();
        this.images = _.uniq(this.images);
        this.$el.append(core.qweb.render('website.og_image_body', {widget: this}));
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a select image from list -> change the preview accordingly.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSelectImg: function (ev) {
        var $img = $(ev.currentTarget);
        this.activeMetaImg = $img.find('img').attr('src');
        this._updateTemplateBody();
    },
    /**
     * Open a mediaDialog to select/upload image.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onClickUploadImg: function (ev) {
        var self = this;
        var $image = $('<img/>');
        var mediaDialog = new weWidgets.MediaDialog(this, {
            onlyImages: true,
            res_model: 'ir.ui.view',
        }, null, $image);
        mediaDialog.open();
        mediaDialog.on('save', this, function (image) {
            var src = image.attr('src');
            self.activeMetaImg = src;
            self.customImgUrl = src;
            self._updateTemplateBody();
        });
    },
});

var SeoConfigurator = Dialog.extend({
    template: 'website.seo_configuration',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/website.seo.xml']
    ),
    canEditTitle: false,
    canEditDescription: false,
    canEditKeywords: false,
    canEditLanguage: false,

    init: function (parent, options) {
        options = options || {};
        _.defaults(options, {
            title: _t('Optimize SEO'),
            buttons: [
                {text: _t('Save'), classes: 'btn-primary', click: this.update},
                {text: _t('Discard'), close: true},
            ],
        });

        this._super(parent, options);
    },
    start: function () {
        var self = this;

        this.$modal.addClass('oe_seo_configuration');

        this.htmlPage = new HtmlPage();

        this.disableUnsavableFields().then(function () {
            // Image selector
            self.metaImageSelector = new MetaImageSelector(self, {
                htmlpage: self.htmlPage,
                title: self.htmlPage.getOgMeta().metaTitle,
                description: self.htmlPage.getOgMeta().metaDescription,
                metaImg : self.metaImg || self.htmlPage.getOgMeta().ogImageUrl,
                pageImages : _.pluck(self.htmlPage.images().get(), 'src'),
            });
            self.metaImageSelector.appendTo(self.$('.js_seo_image'));

            // title and description
            self.metaTitleDescription = new MetaTitleDescription(self, {
                htmlPage: self.htmlPage,
                canEditTitle: self.canEditTitle,
                canEditDescription: self.canEditDescription,
                isIndexed: self.isIndexed,
            });
            self.metaTitleDescription.on('title-changed', self, self.titleChanged);
            self.metaTitleDescription.on('description-changed', self, self.descriptionChanged);
            self.metaTitleDescription.appendTo(self.$('.js_seo_meta_title_description'));

            // keywords
            self.metaKeywords = new MetaKeywords(self, {htmlPage: self.htmlPage});
            self.metaKeywords.appendTo(self.$('.js_seo_meta_keywords'));
        });
    },
    /*
     * Reset meta tags to their initial value if not saved.
     *
     * @private
     */
    destroy: function () {
        if (!this.savedData) {
            this.htmlPage.changeTitle(this.htmlPage.initTitle);
            this.htmlPage.changeDescription(this.htmlPage.initDescription);
        }
        this._super.apply(this, arguments);
    },
    disableUnsavableFields: function () {
        var self = this;
        return this.loadMetaData().then(function (data) {
            // We only need a reload for COW when the copy is happening, therefore:
            // - no reload if we are not editing a view (condition: website_id === undefined)
            // - reload if generic page (condition: website_id === false)
            self.reloadOnSave = data.website_id === undefined ? false : !data.website_id;
            //If website.page, hide the google preview & tell user his page is currently unindexed
            self.isIndexed = (data && ('website_indexed' in data)) ? data.website_indexed : true;
            self.canEditTitle = data && ('website_meta_title' in data);
            self.canEditDescription = data && ('website_meta_description' in data);
            self.canEditKeywords = data && ('website_meta_keywords' in data);
            self.metaImg = data.website_meta_og_img;
            if (!self.canEditTitle && !self.canEditDescription && !self.canEditKeywords) {
                // disable the button to prevent an error if the current page doesn't use the mixin
                // we make the check here instead of on the view because we don't need to check
                // at every page load, just when the rare case someone clicks on this link
                // TODO don't show the modal but just an alert in this case
                self.$footer.find('button[data-action=update]').attr('disabled', true);
            }
        });
    },
    update: function () {
        var self = this;
        var data = {};
        if (this.canEditTitle) {
            data.website_meta_title = this.htmlPage.title();
        }
        if (this.canEditDescription) {
            data.website_meta_description = this.htmlPage.description();
        }
        if (this.canEditKeywords) {
            data.website_meta_keywords = this.metaKeywords.keywordList.keywords().join(', ');
        }
        data.website_meta_og_img = this.metaImageSelector.activeMetaImg;
        this.saveMetaData(data).then(function () {
            // We want to reload if we are editing a generic page
            // because it will become a specific page after this change (COW)
            // and we want the user to be on the page he just created.
            if (self.reloadOnSave) {
                window.location.href = self.htmlPage.url();
            } else {
                self.htmlPage.changeKeywords(self.metaKeywords.keywordList.keywords());
                self.savedData = true;
                self.close();
            }
        });
    },
    getMainObject: function () {
        var repr = $('html').data('main-object');
        var m = repr.match(/(.+)\((\d+),(.*)\)/);
        if (!m) {
            return null;
        } else {
            return {
                model: m[1],
                id: m[2]|0
            };
        }
    },
    loadMetaData: function () {
        var obj = this.getMainObject();
        var def = $.Deferred();
        if (!obj) {
            // return $.Deferred().reject(new Error("No main_object was found."));
            def.resolve(null);
        } else {
            var fields = ['website_meta_title', 'website_meta_description', 'website_meta_keywords'
                            ,'website_meta_og_img'];
            if (obj.model === 'website.page'){
                fields.push('website_indexed');
                fields.push('website_id');
            }
            rpc.query({
                model: obj.model,
                method: 'read',
                args: [[obj.id], fields],
            }).then(function (data) {
                if (data.length) {
                    var meta = data[0];
                    meta.model = obj.model;
                    def.resolve(meta);
                } else {
                    def.resolve(null);
                }
            }).fail(function () {
                def.reject();
            });
        }
        return def;
    },
    saveMetaData: function (data) {
        var obj = this.getMainObject();
        if (!obj) {
            return $.Deferred().reject();
        } else {
            return this._rpc({
                model: obj.model,
                method: 'write',
                args: [[obj.id], data],
            });
        }
    },
    titleChanged: function () {
        var self = this;
        _.defer(function () {
            var title = self.metaTitleDescription.getTitle();
            self.htmlPage.changeTitle(title);
            self.metaImageSelector.setTitle(title);
        });
    },
    descriptionChanged: function () {
        var self = this;
        _.defer(function () {
            var description = self.metaTitleDescription.getDescription();
            self.htmlPage.changeDescription(description);
            self.metaImageSelector.setDescription(description);
        });
    },
});

var SeoMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
        'promote-current-page': '_promoteCurrentPage',
    }),

    init: function (parent, options) {
        this._super(parent, options);

        if ($.deparam.querystring().enable_seo !== undefined) {
            this._promoteCurrentPage();
        }
    },

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Opens the SEO configurator dialog.
     *
     * @private
     */
    _promoteCurrentPage: function () {
        new SeoConfigurator(this).open();
    },
});

websiteNavbarData.websiteNavbarRegistry.add(SeoMenu, '#promote-menu');

return {
    SeoConfigurator: SeoConfigurator,
    SeoMenu: SeoMenu,
};
});
