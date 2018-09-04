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

function analyzeKeyword(htmlPage, keyword) {
    return  htmlPage.isInTitle(keyword) ? {
                title: 'badge badge-success',
                description: "This keyword is used in the page title",
            } : htmlPage.isInDescription(keyword) ? {
                title: 'badge badge-primary',
                description: "This keyword is used in the page description",
            } : htmlPage.isInBody(keyword) ? {
                title: 'badge badge-info',
                description: "This keyword is used in the page content."
            } : {
                title: 'badge badge-secondary',
                description: "This keyword is not used anywhere on the page."
            };
}

var Suggestion = Widget.extend({
    template: 'website.seo_suggestion',
    xmlDependencies: ['/website/static/src/xml/website.seo.xml'],
    events: {
        'click .js_seo_suggestion': 'select',
    },

    init: function (parent, options) {
        this.root = options.root;
        this.keyword = options.keyword;
        this.language = options.language;
        this.htmlPage = options.page;
        this._super(parent);
    },
    start: function () {
        this.htmlPage.on('title-changed', this, this.renderElement);
        this.htmlPage.on('description-changed', this, this.renderElement);
    },
    analyze: function () {
        return analyzeKeyword(this.htmlPage, this.keyword);
    },
    highlight: function () {
        return this.analyze().title;
    },
    tooltip: function () {
        return this.analyze().description;
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
        this.htmlPage = options.page;
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
        var regex = new RegExp(self.root, 'gi');
        keywords = _.map(_.uniq(keywords), function (word) {
            return word.replace(regex, '').trim();
        });
        // TODO Order properly ?
        _.each(keywords, function (keyword) {
            if (keyword) {
                var suggestion = new Suggestion(self, {
                    root: self.root,
                    language: self.language,
                    keyword: keyword,
                    page: self.htmlPage,
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
    maxWordsPerKeyword: 4, // TODO Check

    init: function (parent, options) {
        this.keyword = options.word;
        this.language = options.language;
        this.htmlPage = options.page;
        this._super(parent);
    },
    start: function () {
        this.htmlPage.on('title-changed', this, this.updateLabel);
        this.htmlPage.on('description-changed', this, this.updateLabel);
        this.suggestionList = new SuggestionList(this, {
            root: this.keyword,
            language: this.language,
            page: this.htmlPage,
        });
        this.suggestionList.on('selected', this, function (word, language) {
            this.trigger('selected', word, language);
        });
        this.suggestionList.appendTo(this.$('.js_seo_keyword_suggestion'));
    },
    analyze: function () {
        return analyzeKeyword(this.htmlPage, this.keyword);
    },
    highlight: function () {
        return this.analyze().title;
    },
    tooltip: function () {
        return this.analyze().description;
    },
    updateLabel: function () {
        var cssClass = 'oe_seo_keyword js_seo_keyword ' + this.highlight();
        this.$('.js_seo_keyword').attr('class', cssClass);
        this.$('.js_seo_keyword').attr('title', this.tooltip());
    },
    destroy: function () {
        this.trigger('removed');
        this._super();
    },
});

var KeywordList = Widget.extend({
    template: 'website.seo_list',
    xmlDependencies: ['/website/static/src/xml/website.seo.xml'],
    maxKeywords: 10,

    init: function (parent, options) {
        this.htmlPage = options.page;
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
                page: this.htmlPage,
            });
            keyword.on('removed', self, function () {
               self.trigger('list-not-full');
               self.trigger('removed', word);
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
        this.title = options.title || _t('Title');
        this.url = options.url;
        this.description = options.description || _t("Description");
        if (this.description.length > 160) {
            this.description = this.description.substring(0,159) + '…';
        }
        this._super(parent);
    },
});

var HtmlPage = Class.extend(mixins.PropertiesMixin, {
    url: function () {
        var url = window.location.href;
        var hashIndex = url.indexOf('#');
        return hashIndex >= 0 ? url.substring(0, hashIndex) : url;
    },
    title: function () {
        var $title = $('title');
        return ($title.length > 0) && $title.text() && $title.text().trim();
    },
    changeTitle: function (title) {
        // TODO create tag if missing
        $('title').text(title);
        this.trigger('title-changed', title);
    },
    description: function () {
        var $description = $('meta[name=description]');
        return ($description.length > 0) && ($description.attr('content') && $description.attr('content').trim());
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
    isInBody: function (text) {
        return new RegExp(WORD_SEPARATORS_REGEX+text+WORD_SEPARATORS_REGEX, 'gi').test(this.bodyText());
    },
    isInTitle: function (text) {
        return new RegExp(WORD_SEPARATORS_REGEX+text+WORD_SEPARATORS_REGEX, 'gi').test(this.title());
    },
    isInDescription: function (text) {
        return new RegExp(WORD_SEPARATORS_REGEX+text+WORD_SEPARATORS_REGEX, 'gi').test(this.description());
    },
});

var Tip = Widget.extend({
    template: 'website.seo_tip',
    xmlDependencies: ['/website/static/src/xml/website.seo.xml'],
    events: {
        'closed.bs.alert': 'destroy',
    },

    init: function (parent, options) {
        this.message = options.message;
        // cf. http://getbootstrap.com/components/#alerts
        // success, info, warning or danger
        this.type = options.type || 'info';
        this._super(parent);
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
        this.canEditTitle = !!options.canEditTitle;
        this.canEditDescription = !!options.canEditDescription;
        this.isIndexed = !!options.isIndexed;
        this.showKeywords = !!options.showKeywords;
        this.initTitle = options.title || '';
        this.initDescription = options.description || '';
        this.initKeywords = options.keywords || '';
        this.url = options.url || '/';
        this._super(parent, options);
    },
    /**
     * @override
     */
    start: function () {
        this.$title = this.$('input[name=website_meta_title]');
        this.$description = this.$('textarea[name=website_meta_description]');
        this.$keywords = this.$('input[name=website_meta_keywords]');
        this.$warning = this.$('div#website_meta_description_warning');
        this.$preview = this.$('.js_seo_preview');

        this._renderPreview();

        if (!this.canEditTitle) {
            this.$title.attr('disabled', true);
        }
        if (!this.canEditDescription) {
            this.$description.attr('disabled', true);
        }

        this.$title.val(this.initTitle);
        this.$description.val(this.initDescription);
        this.$keywords.val(this.initKeywords);

        this._descriptionOnChange();
    },
    /**
     * Get the current title
     */
    getTitle: function () {
        return this.$title.val();
    },
    /**
     * Get the current description
     */
    getDescription: function () {
        return this.$description.val();
    },
    /**
     * Get the current keywords
     */
    getKeywords: function () {
        return this.$keywords.val();
    },
    /**
     * Update the url to show on the preview
     */
    setUrl: function (url) {
        this.url = url || '/';
        this._renderPreview();
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

        // TODO SEB check lead scoring add a checkbox here?!

        // TODO SEB put back the 2 columns: duplicate and delete (the one in debug stays debug)

        // TODO SEB remove the buttons from the modal (duplicate and elete)

        // TODO SEB add duplicate and delete in the pages menu
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
                url: this.url,
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
        this.metaDescription = data.description || '';
        this.activeMetaImg = data.metaImg;
        this.serverUrl = window.location.origin;
        data.pageImages.unshift(_.str.sprintf('/web/image/res.company/%s/logo', odoo.session_info.website_company_id));
        this.images = _.uniq(data.pageImages);
        this.customImgUrl = _.contains(data.pageImages, data.metaImg) ? false : data.metaImg;
        this._super(parent);
    },
    setTitle: function (title) {
        this.metaTitle = title;
        this._updateTemplateBody();
    },
    setDescription: function (description) {
        this.metaDescription = description;
        this._updateTemplateBody();
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
    events: {
        'keyup input[name=seo_page_keywords]': 'confirmKeyword',
        'click button[data-action=add]': 'addKeyword',
    },
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

        this.keywordList = new KeywordList(self, { page: this.htmlPage });
        this.keywordList.on('list-full', self, function () {
            self.$('input[name=seo_page_keywords]').attr({
                readonly: 'readonly',
                placeholder: "Remove a keyword first"
            });
            self.$('button[data-action=add]').prop('disabled', true).addClass('disabled');
        });
        this.keywordList.on('list-not-full', self, function () {
            self.$('input[name=seo_page_keywords]').removeAttr('readonly').attr('placeholder', "");
            self.$('button[data-action=add]').prop('disabled', false).removeClass('disabled');
        });
        this.keywordList.on('selected', self, function (word, language) {
            self.keywordList.add(word, language);
        });
        this.keywordList.on('content-updated', self, function (removed) {
            self.updateTable(removed);
        });
        this.keywordList.insertAfter(this.$('.table thead'));

        this.disableUnsavableFields().then(function () {
            self.metaTitleDescription = new MetaTitleDescription(self, {
                canEditTitle: self.canEditTitle,
                canEditDescription: self.canEditDescription,
                isIndexed: self.isIndexed,
                title: self.htmlPage.title(),
                description: self.htmlPage.description(),
                url: self.htmlPage.url(),
            });
            self.metaTitleDescription.on('title-changed', self, self.titleChanged);
            self.metaTitleDescription.on('description-changed', self, self.descriptionChanged);
            self.metaTitleDescription.appendTo(self.$('.js_seo_meta_title_description'));
        });

        this.getLanguages();
        this.updateTable();
    },
    getLanguages: function () {
        var self = this;
        this._rpc({
            model: 'website',
            method: 'get_languages',
            args: [[weContext.get().website_id]],
            context: weContext.get(),
        }).then( function (data) {
            self.$('#language-box').html(core.qweb.render('Configurator.language_promote', {
                'language': data,
                'def_lang': weContext.get().lang
            }));
        });
    },
    disableUnsavableFields: function () {
        var self = this;
        return loadMetaData().then(function (data) {
            // no reload if not on page (website_id === undefined)
            // reload if generic page (website_id === false)
            self.reloadOnSave = data.website_id === undefined ? false : !data.website_id;
            //If website.page, hide the google preview & tell user his page is currently unindexed 
            self.isIndexed = (data && ('website_indexed' in data)) ? data.website_indexed : true;
            self.canEditTitle = data && ('website_meta_title' in data);
            self.canEditDescription = data && ('website_meta_description' in data);
            self.canEditKeywords = data && ('website_meta_keywords' in data);

            if (!self.canEditTitle && !self.canEditDescription) {
                self.$footer.find('button[data-action=update]').attr('disabled', true);
            }
        });
    },
    suggestImprovements: function () {
        var self = this;
        var tips = [];
        _.each(tips, function (tip) {
            displayTip(tip.message, tip.type);
        });

        function displayTip(message, type) {
            new Tip(self, {
               message: message,
               type: type,
            }).appendTo(self.$('.js_seo_tips'));
        }
    },
    confirmKeyword: function (e) {
        if (e.keyCode === 13) {
            this.addKeyword();
        }
    },
    addKeyword: function (word) {
        var $input = this.$('input[name=seo_page_keywords]');
        var $language = this.$('select[name=seo_page_language]');
        var keyword = _.isString(word) ? word : $input.val();
        var language = $language.val().toLowerCase();
        this.keywordList.add(keyword, language);
        $input.val('').focus();
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
            data.website_meta_keywords = this.keywordList.keywords().join(', ');
            this.htmlPage.changeKeywords(self.keywordList.keywords());
        }
        saveMetaData(data).then(function () {
            reloadOrClose.call(self);
        });
    },
    titleChanged: function () {
        var title = this.metaTitleDescription.getTitle();
        this.htmlPage.changeTitle(title);
    },
    descriptionChanged: function () {
        var description = this.metaTitleDescription.getDescription();
        this.htmlPage.changeDescription(description);
    },
    updateTable : function (removed) {
        var val = removed ? (this.$el.find('tbody > tr').length - 1) : (this.$el.find('tbody > tr').length);
        this.$('table').toggleClass('js_seo_has_content', val > 0 );
        this.$el.scrollTop(this.$el[0].scrollHeight);
    },
});

var SocialShare = Dialog.extend({
    template: 'website.social_share',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/website.seo.xml']
    ),

    init: function (parent, options) {
        options = options || {};
        _.defaults(options, {
            title: _t('Social Share'),
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

        loadMetaData().then(function (data) {
            // no reload if not on page (website_id === undefined)
            // reload if generic page (website_id === false)
            self.reloadOnSave = data.website_id === undefined ? false : !data.website_id;
            self.metaImg = data.website_meta_og_img;
            self.metaImageSelector = new MetaImageSelector(self, {
                title: self.htmlPage.getOgMeta().metaTitle,
                description: self.htmlPage.getOgMeta().metaDescription,
                metaImg : self.metaImg || self.htmlPage.getOgMeta().ogImageUrl,
                pageImages : _.pluck(self.htmlPage.images().get(), 'src'),
            });
            self.metaImageSelector.appendTo(self.$('.js_seo_image'));
        });
    },
    update: function () {
        var self = this;
        saveMetaData({
            website_meta_og_img: this.metaImageSelector.activeMetaImg,
        }).then(function () {
            reloadOrClose.call(self);
        });
    },
});

var SeoMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
        'optimize-seo': '_optimizeSeo',
        'social-share': '_socialShare',
    }),

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Opens the SEO configurator dialog.
     *
     * @private
     */
    _optimizeSeo: function () {
        new SeoConfigurator(this).open();
    },

    /**
     * Opens the Social Share configurator dialog.
     *
     * @private
     */
    _socialShare: function () {
        new SocialShare(this).open();
    },
});

function reloadOrClose() {
    // We want to reload if we are editing a generic page
    // because it will become a specific page after this change
    // and we want the user to be on the page he just created.
    if (this.reloadOnSave) {
        window.location.reload(true);
    } else {
        this.close();
    }
}

function getMainObject() {
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
}

function loadMetaData() {
    var obj = getMainObject();
    var def = $.Deferred();
    if (!obj) {
        // return $.Deferred().reject(new Error("No main_object was found."));
        def.resolve(null);
    } else {
        var fields = [
            'website_meta_title',
            'website_meta_description',
            'website_meta_keywords',
            'website_meta_og_img'
        ];
        if (obj.model === 'website.page'){
            fields.push('website_indexed');
            fields.push('website_id');
        }
        rpc.query({
            model: obj.model,
            method: 'read',
            args: [[obj.id], fields, weContext.get()],
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
}

function saveMetaData(data) {
    var obj = getMainObject();
    if (!obj) {
        return $.Deferred().reject();
    } else {
        return rpc.query({
            model: obj.model,
            method: 'write',
            args: [[obj.id], data, weContext.get()],
        });
    }
}

websiteNavbarData.websiteNavbarRegistry.add(SeoMenu, '#promote-menu');

return {
    HtmlPage: HtmlPage,
    MetaImageSelector: MetaImageSelector,
    MetaTitleDescription: MetaTitleDescription,
    Preview: Preview,
    SeoConfigurator: SeoConfigurator,
    SeoMenu: SeoMenu,
    SocialShare: SocialShare,
};
});
