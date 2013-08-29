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

    function cleanupKeyword (word) {
        return word ? word.replace(/[,;.:]+/g, " ").replace(/ +/g, " ").trim() : "";
    }

    website.seo = {};

    website.seo.Tip = openerp.Widget.extend({
        template: 'website.seo_tip',
        events: {
            'click button[data-action=close]': 'destroy',
        },
        init: function (parent, options) {
            this._super(parent);
            this.message = options.message;
            // info, error or success
            this.type = options.type;
        },
    });

    website.seo.Keyword = openerp.Widget.extend({
        template: 'website.seo_keyword',
        events: {
            'click a[data-action=remove-keyword]': 'destroy',
        },
        init: function (parent, options) {
            this._super(parent);
            this.keyword = options.keyword;
            this.onDelete = options.onDelete;
        },
        destroy: function () {
            if (_.isFunction(this.onDelete)) {
                this.onDelete(this.keyword);
            }
            this._super();
        },
    });

    website.seo.PageParser = openerp.Class.extend({
        init: function () {
            this._url = this._currentURL();
            this._title = $(document.title).text();
            this._headers = {};

            var self = this;
            _.each([ 'h1', 'h2', 'h3'], function (header) {
                self._headers[header] = $(header).map(function () {
                    return $(this).text();
                }).get();
            });
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
        _currentURL: function () {
            var url = window.location.href;
            var hashIndex = url.indexOf('#');
            return hashIndex >= 0 ? url.substring(0, hashIndex) : url;
        },
        keywordSuggestions: function () {
            var headers = this.headers();
            return _.map(_.uniq(headers.h1.concat(headers.h2)),
                         cleanupKeyword);
        },
    });
    website.seo.Configurator = openerp.Widget.extend({
        template: 'website.seo_configuration',
        events: {
            'keypress input[name=seo_page_keywords]': 'confirmKeyword',
            'click button[data-action=add]': 'addKeyword',
            'click a[data-action=update]': 'update',
            'hidden': 'destroy'
        },

        maxTitleSize: 65,
        maxDescriptionSize: 155,
        maxNumberOfKeywords: 10,
        maxWordsPerKeyword: 4,

        start: function () {
            var pageParser = new website.seo.PageParser();
            var currentKeywords = this.keywords;
            this.$el.find('.js_seo_page_url').text(pageParser.url());
            this.$el.find('input[name=seo_page_title]').val(pageParser.title());
            this.$el.find('input[name=seo_page_keywords]').typeahead({
                items: 4,
                source: function () {
                    var suggestions = pageParser.keywordSuggestions();
                    var alreadyChosen = currentKeywords();
                    return _.difference(suggestions, alreadyChosen);
                },
            });
            this.checkBestPractices(pageParser);
            $(document.body).addClass('oe_stop_scrolling');
            this.$el.modal();
        },
        checkBestPractices: function (parser) {
            var pageParser = parser || new website.seo.PageParser();
            if (pageParser.headers()['h1'].length > 1) {
                new website.seo.Tip(this, {
                   message: "You have more than one &lt;h1&gt; tag on the page.",
                   type: 'error'
                }).appendTo(this.$el.find('.js_seo_tips'));
            }
        },
        currentPage: function () {
            var url = window.location.href;
            var hashIndex = url.indexOf('#');
            return hashIndex > 0 ? url.substring(0, hashIndex): url;
        },
        keywords: function () {
            return _.uniq($('.js_seo_keyword').map(function () {
                return $(this).text();
            }));
        },
        isExistingKeyword: function (word) {
            return _.contains(this.keywords(), word);
        },
        isKeywordListFull: function () {
            return this.keywords().length >= this.maxNumberOfKeywords;
        },
        confirmKeyword: function (e) {
            if (e.keyCode == 13) {
                this.addKeyword();
                this.$el.find('input[name=seo_page_keywords]').val("");
            }
        },
        addKeyword: function () {
            var $modal = this.$el;
            function enableNewKeywords () {
                $modal.find('input[name=seo_page_keywords]')
                    .removeAttr('readonly').attr('placeholder', "");
                $modal.find('button[data-action=add]')
                    .prop('disabled', false).removeClass('disabled');
            }
            function disableNewKeywords () {
                $modal.find('input[name=seo_page_keywords]')
                    .attr('readonly', "readonly")
                    .attr('placeholder', "Remove a keyword first");
                $modal.find('button[data-action=add]')
                    .prop('disabled', true).addClass('disabled');
            }
            var candidate = this.$el.find('input[name=seo_page_keywords]').val();
            var word = cleanupKeyword(candidate);
            if (word && !this.isKeywordListFull() && !this.isExistingKeyword(word)) {
                new website.seo.Keyword(this, {
                    keyword: word,
                    onDelete: enableNewKeywords
                }).appendTo(this.$el.find('.js_seo_keywords_list'));
                this.scrollDown();
            }
            if (this.isKeywordListFull()) {
                disableNewKeywords();
            }
        },
        scrollDown: function () {
            var $body = this.$el.find('.modal-body');
            $body.animate({
                scrollTop: $body[0].scrollHeight
            }, 500);
        },
        update: function () {
            // TODO: Persist changes
        },
        destroy: function () {
            $(document.body).removeClass('oe_stop_scrolling');
            this._super();
        },
    });
})();
