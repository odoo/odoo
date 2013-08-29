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
    website.seo.cleanupKeyword = function (word) {
        return word ? word.replace(/[,;.:]+/g, " ").replace(/ +/g, " ").trim() : "";
    };
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
                         website.seo.cleanupKeyword);
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
                source: function () {
                    var suggestions = pageParser.keywordSuggestions();
                    var alreadyChosen = currentKeywords();
                    return _.difference(suggestions, alreadyChosen);
                },
                items: 4
            });

            $(document.body).addClass('oe_stop_scrolling');
            this.$el.modal();
        },
        currentPage: function () {
            var url = window.location.href;
            var hashIndex = url.indexOf('#');
            return hashIndex > 0 ? url.substring(0, hashIndex): url;
        },
        keywords: function () {
            return _.uniq($('.js_seo_keyword').map(function () {
                return $(this).text();
            }).get());
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
                    .removeAttr('readonly').attr('placeholder', "New keyword");
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
            var word = website.seo.cleanupKeyword(candidate);
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
