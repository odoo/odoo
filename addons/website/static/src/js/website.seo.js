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
        return word ? word.replace(/[,;.:<>]+/g, " ").replace(/ +/g, " ").trim() : "";
    }

    website.seo = {};

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
        }
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
            this.onDelete = options.onDelete;
            this._super(parent);
        },
        destroy: function () {
            if (_.isFunction(this.onDelete)) {
                this.onDelete(this.keyword);
            }
            this._super();
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
            this._addToSelection = function (keyword) {
                if (_.isFunction(parent.addKeyword)) {
                    parent.addKeyword(keyword, parent.$el, 'info');
                }
            };
            this._super(parent);
        },
        addToSelection: function () {
            this._addToSelection(this.keyword);
        },
    });

    website.seo.PageParser = openerp.Class.extend({
        init: function () {
            this._company = $('meta[name="openerp.company"]').attr('value');
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
        company: function () {
            return this._company;
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
                        new website.seo.Suggestion(self, {
                            keyword: keyword
                        }).appendTo($modal.find('.js_seo_company_suggestions'));
                    }
                });
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
                this.$el.find('input[name=seo_page_keywords]').val("");
            }
        },
        addKeyword: function (keyword, $el, type) {
            var $modal = $el || this.$el;
            function keywords () {
                return $('.js_seo_keyword').map(function () {
                    return $(this).data('keyword');
                });
            }
            function isKeywordListFull () {
                return keywords().length >= 10;
            }
            function isExistingKeyword (word) {
                return _.contains(keywords(), word);
            }
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
            var candidate = keyword || $modal.find('input[name=seo_page_keywords]').val();
            var word = cleanupKeyword(candidate);
            if (word && !isKeywordListFull() && !isExistingKeyword(word)) {
                new website.seo.Keyword(this, {
                    keyword: word,
                    type: type,
                    onDelete: enableNewKeywords
                }).appendTo($modal.find('.js_seo_keywords_list'));
            }
            if (isKeywordListFull()) {
                disableNewKeywords();
            }
        },
        update: function () {
            // TODO: Persist changes
        },
    });
})();
