(function () {
    'use strict';

    var website = openerp.website;
    website.EditorBar.include({
        events: _.extend({}, website.EditorBar.prototype.events, {
            'click a[data-action=promote-current-page]': 'promotePage',
        }),
        promotePage: function () {
            (new website.seo.Configurator()).appendTo($(document.body));
        },
    });

    website.seo = {};

    website.seo.PageParser = openerp.Class.extend({
        init: function () {
            this._company = $('meta[name="openerp.company"]').attr('value');
            this._url = this._currentURL();
            this._title = $(document.title).text();
            this._headers = {};
            var _images = [];
            this._images = _images;

            var self = this;
            _.each([ 'h1', 'h2', 'h3'], function (header) {
                self._headers[header] = $(header).map(function () {
                    return $(this).text();
                }).get();
            });
            $('#wrap img').each(function () {
                var $this = $(this);
                var img = {
                    src: $this.attr('src'),
                    alt: $this.attr('alt'),
                };
                _images.push(img);
            });
        },
        _currentURL: function () {
            var url = window.location.href;
            var hashIndex = url.indexOf('#');
            return hashIndex >= 0 ? url.substring(0, hashIndex) : url;
        },
        url: function () {
            return this._url;
        },
        title: function () {
            return this._title;
        },
        headers: function () {
            return this._headers;
        },
        images: function () {
            return this._images;
        },
        company: function () {
            return this._company;
        },
    });


    website.seo.Tip = openerp.Widget.extend({
        template: 'website.seo_tip',
        events: {
            'closed.bs.alert': 'destroy',
        },
        init: function (parent, options) {
            this.message = options.message;
            // success, info, warning or danger
            this.type = options.type || 'info';
            this._super(parent);
        },
    });

    website.seo.Keyword = openerp.Widget.extend({
        template: 'website.seo_keyword',
        events: {
            'click a[data-action=remove-keyword]': 'destroy',
        },
        init: function (parent, options) {
            this.keyword = options.keyword;
            // default, primary, success, info, warning, danger
            this.type = options.type || 'default';
            this._super(parent);
        },
        destroy: function () {
            this.trigger('removed');
            this._super();
        },
    });

    website.seo.KeywordList = openerp.Widget.extend({
        template: 'website.seo_keyword_list',
        maxKeywords: 10,
        cleanupKeyword: function (word) {
            return word ? word.replace(/[,;.:<>]+/g, " ").replace(/ +/g, " ").trim() : "";
        },
        keywords: function () {
            return this.$el.find('.js_seo_keyword').map(function () {
                return $(this).data('keyword');
            });
        },
        suggestions: function () {
            // TODO: Refactor
            return $('.js_seo_suggestion').map(function () {
                return $(this).data('keyword');
            });
        },
        isKeywordListFull: function () {
            return this.keywords().length >= this.maxKeywords;
        },
        isExistingKeyword: function (word) {
            return _.contains(this.keywords(), word);
        },
        determineType: function (word) {
            return _.contains(this.suggestions(), word) ? 'success' : 'default';
        },
        add: function (word) {
            var self = this;
            var word = this.cleanupKeyword(word);
            if (!this.isKeywordListFull() && !this.isExistingKeyword(word)) {
                var type = this.determineType(word);
                var keyword = new website.seo.Keyword(this, {
                    keyword: word,
                    type: type,
                });
                keyword.on('removed', null, function () {
                   self.trigger('list-not-full');
                });
                keyword.appendTo(this.$el);
            }
            if (this.isKeywordListFull()) {
                self.trigger('list-full');
            }
        },
    });

    website.seo.Suggestion = openerp.Widget.extend({
        template: 'website.seo_suggestion',
        events: {
            'click .js_seo_suggestion': 'addToSelection'
        },
        init: function (parent, options) {
            this.keyword = options.keyword;
            // default, primary, success, info, warning, danger
            this.type = options.type || 'default';
            this._super(parent);
        },
        addToSelection: function () {
            this.trigger('selected');
        },
    });

    website.seo.Image = openerp.Widget.extend({
        template: 'website.seo_image',
        init: function (parent, options) {
            this.src = options.src;
            this.alt = options.alt;
            this._super(parent);
        }
    });

    website.seo.Configurator = openerp.Widget.extend({
        template: 'website.seo_configuration',
        events: {
            'keypress input[name=seo_page_keywords]': 'confirmKeyword',
            'click button[data-action=add]': 'addKeyword',
            'click a[data-action=update]': 'update',
            'hidden.bs.modal': 'destroy'
        },

        maxTitleSize: 65,
        maxDescriptionSize: 155,
        maxWordsPerKeyword: 4,

        start: function () {
            var pageParser = new website.seo.PageParser();
            this.$el.find('.js_seo_page_url').text(pageParser.url());
            this.$el.find('input[name=seo_page_title]').val(pageParser.title());
            this.checkBestPractices(pageParser);
            this.displayKeywordSuggestions(pageParser);
            this.displayImages(pageParser);
            this.keywordList = new website.seo.KeywordList(this);
            this.keywordList.appendTo(this.$el.find('.js_seo_keywords_list'));

            var $modal = this.$el;
            this.keywordList.on('list-full', null, function () {
                $modal.find('input[name=seo_page_keywords]')
                    .attr('readonly', "readonly")
                    .attr('placeholder', "Remove a keyword first");
                $modal.find('button[data-action=add]')
                    .prop('disabled', true).addClass('disabled');
            });
            this.keywordList.on('list-not-full', null, function () {
                $modal.find('input[name=seo_page_keywords]')
                    .removeAttr('readonly').attr('placeholder', "");
                $modal.find('button[data-action=add]')
                    .prop('disabled', false).removeClass('disabled');
            });
            this.$el.modal();
        },
        checkBestPractices: function (parser) {
            var tips = [];
            var self = this;
            function displayTip(message, type) {
                new website.seo.Tip(this, {
                   message: message,
                   type: type
                }).appendTo(self.$el.find('.js_seo_tips'));
            }
            var pageParser = parser || new website.seo.PageParser();
            if (pageParser.headers()['h1'].length === 0) {
                tips.push({
                    type: 'warning',
                    message: "You don't have an &lt;h1&gt; tag on your page."
                });
            }
            if (pageParser.headers()['h1'].length > 1) {
                tips.push({
                    type: 'warning',
                    message: "You have more than one &lt;h1&gt; tag on your page."
                });
            }

            if (tips.length > 0) {
                _.each(tips, function (tip) {
                    displayTip(tip.message, tip.type);
                });
            } else {
                displayTip("Your page makup is appropriate for search engines.", 'success');
            }
        },
        displayKeywordSuggestions: function (pageParser) {
            var $modal = this.$el;
            var companyName = pageParser.company().toLowerCase();
            var requestURL = "http://seo.eu01.aws.af.cm/suggest/" + encodeURIComponent(companyName);
            $modal.find('.js_seo_company_suggestions').append("Loading...");
            var self = this;
            $.getJSON(requestURL, function (list) {
                $modal.find('.js_seo_company_suggestions').empty();
                var nameRegex = new RegExp(companyName, "gi");
                var cleanList = _.map(list, function (word) {
                    return word.replace(nameRegex, "").trim();
                });
                cleanList.push(companyName);
                _.each(_.uniq(cleanList), function (keyword) {
                    if (keyword) {
                        var suggestion = new website.seo.Suggestion(self, {
                            keyword: keyword
                        });
                        suggestion.on('selected', self, function () {
                           self.addKeyword(keyword);
                        });
                        suggestion.appendTo($modal.find('.js_seo_company_suggestions'));
                    }
                });
            });
        },
        displayImages: function (pageParser) {
            var $container = this.$el.find('.js_seo_images');
            $container.empty();
            var self = this;
            _.each(pageParser.images(), function (image) {
                new website.seo.Image(self, image).appendTo($container);
            });
        },
        currentPage: function () {
            var url = window.location.href;
            var hashIndex = url.indexOf('#');
            return hashIndex > 0 ? url.substring(0, hashIndex): url;
        },
        confirmKeyword: function (e) {
            if (e.keyCode == 13) {
                this.addKeyword();
            }
        },
        addKeyword: function (keyword) {
            var $modal = this.$el;
            var candidate = keyword || $modal.find('input[name=seo_page_keywords]').val();
            this.keywordList.add(candidate);
            $modal.find('input[name=seo_page_keywords]').val("");
        },
        update: function () {
            // TODO: Persist changes
        },
    });
})();
