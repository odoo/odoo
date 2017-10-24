odoo.define('website.seo', function (require) {
'use strict';

var core = require('web.core');
var Class = require('web.Class');
var Dialog = require('web.Dialog');
var mixins = require('web.mixins');
var rpc = require('web.rpc');
var Widget = require('web.Widget');
var weContext = require('web_editor.context');
var websiteNavbarData = require('website.navbar');

var _t = core._t;

// This replaces \b, because accents(e.g. à, é) are not seen as word boundaries.
// Javascript \b is not unicode aware, and words beginning or ending by accents won't match \b
var WORD_SEPARATORS_REGEX = '([\\u2000-\\u206F\\u2E00-\\u2E7F\'!"#\\$%&\\(\\)\\*\\+,\\-\\.\\/:;<=>\\?¿¡@\\[\\]\\^_`\\{\\|\\}~\\s]+|^|$)';

function analyzeKeyword(htmlPage, keyword) {
    return  htmlPage.isInTitle(keyword) ? {
                title: 'label label-success',
                description: "This keyword is used in the page title",
            } : htmlPage.isInDescription(keyword) ? {
                title: 'label label-primary',
                description: "This keyword is used in the page description",
            } : htmlPage.isInBody(keyword) ? {
                title: 'label label-info',
                description: "This keyword is used in the page content."
            } : {
                title: 'label label-default',
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
        this.title = options.title;
        this.url = options.url;
        this.description = options.description || "[ The description will be generated by google unless you specify one ]";
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
        this.trigger('keywords-changed', keywords);
    },
    headers: function (tag) {
        return $('#wrap '+tag).map(function () {
            return $(this).text();
        });
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
        return $('body').children().not('.js_seo_configuration').text();
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

var SeoConfigurator = Dialog.extend({
    template: 'website.seo_configuration',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/website/static/src/xml/website.seo.xml']
    ),
    events: {
        'keyup input[name=seo_page_keywords]': 'confirmKeyword',
        'blur input[name=seo_page_title]': 'titleChanged',
        'blur textarea[name=seo_page_description]': 'descriptionChanged',
        'click button[data-action=add]': 'addKeyword',
    },
    canEditTitle: false,
    canEditDescription: false,
    canEditKeywords: false,
    canEditLanguage: false,
    maxTitleSize: 65,
    maxDescriptionSize: 160,  // TODO master: remove me and add warning

    init: function (parent, options) {
        options = options || {};
        _.defaults(options, {
            title: _t('Promote Page'),
            subtitle: _t('Get this page efficiently referenced in search engines to attract more visitors.'),
            buttons: [
                {text: _t('Save'), classes: 'btn-primary', click: this.update},
                {text: _t('Discard'), close: true},
            ],
        });

        this._super(parent, options);
    },
    start: function () {
        var self = this;

        this.$modal.addClass('oe_seo_configuration js_seo_configuration');

        this.htmlPage = new HtmlPage();
        this.$('.js_seo_page_url').text(this.htmlPage.url());
        this.$('input[name=seo_page_title]').val(this.htmlPage.title());
        this.$('textarea[name=seo_page_description]').val(this.htmlPage.description());

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
        this.disableUnsavableFields().then(function(){
            self.renderPreview();
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
        return this.loadMetaData().then(function (data) {
            //If website.page, hide the google preview & tell user his page is currently unindexed 
            self.isIndexed = (data && ('website_indexed' in data)) ? data.website_indexed : true;
            self.canEditTitle = data && ('website_meta_title' in data);
            self.canEditDescription = data && ('website_meta_description' in data);
            self.canEditKeywords = data && ('website_meta_keywords' in data);
            if (!self.canEditTitle) {
                self.$('input[name=seo_page_title]').attr('disabled', true);
            }
            if (!self.canEditDescription) {
                self.$('textarea[name=seo_page_description]').attr('disabled', true);
            }
            if (!self.canEditTitle && !self.canEditDescription && !self.canEditKeywords) {
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
        }
        this.saveMetaData(data).then(function () {
           self.htmlPage.changeKeywords(self.keywordList.keywords());
           self.close();
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
            var fields = ['website_meta_title', 'website_meta_description', 'website_meta_keywords'];
            if (obj.model == 'website.page'){
                fields.push('website_indexed');
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
    },
    saveMetaData: function (data) {
        var obj = this.getMainObject();
        if (!obj) {
            return $.Deferred().reject();
        } else {
            return rpc.query({
                model: obj.model,
                method: 'write',
                args: [[obj.id], data, weContext.get()],
            });
        }
    },
    titleChanged: function () {
        var self = this;
        _.defer(function () {
            var title = self.$('input[name=seo_page_title]').val();
            self.htmlPage.changeTitle(title);
            self.renderPreview();
        });
    },
    descriptionChanged: function () {
        var self = this;
        _.defer(function () {
            var description = self.$('textarea[name=seo_page_description]').val();
            self.htmlPage.changeDescription(description);
            self.renderPreview();
        });
    },
    renderPreview: function () {
        var indexed = this.isIndexed;
        var preview = "";
        if(indexed){
            preview = new Preview(this, {
                title: this.htmlPage.title(),
                description: this.htmlPage.description(),
                url: this.htmlPage.url(),
            });
        }
        else{
            preview = new Preview(this, {
                description: _("You have hidden this page from search results. It won't be indexed by search engines."),
            });
        }
        var $preview = this.$('.js_seo_preview');
        $preview.empty();
        preview.appendTo($preview);
    },
    updateTable : function (removed) {
        var self = this,
             val = removed ? (this.$el.find('tbody > tr').length - 1) : (this.$el.find('tbody > tr').length);
        this.$('table').toggleClass('js_seo_has_content', val > 0 );
        this.$el.scrollTop(self.$el[0].scrollHeight);
    },
});

var SeoMenu = websiteNavbarData.WebsiteNavbarActionWidget.extend({
    actions: _.extend({}, websiteNavbarData.WebsiteNavbarActionWidget.prototype.actions || {}, {
        'promote-current-page': '_promoteCurrentPage',
    }),

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
