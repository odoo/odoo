odoo.define('website_forum.website_forum', function (require) {
'use strict';

var core = require('web.core');
var weDefaultOptions = require('web_editor.wysiwyg.default_options');
var wysiwygLoader = require('web_editor.loader');
var publicWidget = require('web.public.widget');
var session = require('web.session');
var qweb = core.qweb;

var _t = core._t;

publicWidget.registry.websiteForum = publicWidget.Widget.extend({
    selector: '.website_forum',
    xmlDependencies: ['/website_forum/static/src/xml/website_forum_share_templates.xml'],
    events: {
        'click .karma_required': '_onKarmaRequiredClick',
        'mouseenter .o_js_forum_tag_follow': '_onTagFollowBoxMouseEnter',
        'mouseleave .o_js_forum_tag_follow': '_onTagFollowBoxMouseLeave',
        'mouseenter .o_forum_user_info': '_onUserInfoMouseEnter',
        'mouseleave .o_forum_user_info': '_onUserInfoMouseLeave',
        'mouseleave .o_forum_user_bio_expand': '_onUserBioExpandMouseLeave',
        'click .flag:not(.karma_required)': '_onFlagAlertClick',
        'click .vote_up:not(.karma_required), .vote_down:not(.karma_required)': '_onVotePostClick',
        'click .o_js_validation_queue a[href*="/validate"]': '_onValidationQueueClick',
        'click .o_wforum_validate_toggler:not(.karma_required)': '_onAcceptAnswerClick',
        'click .o_wforum_favourite_toggle': '_onFavoriteQuestionClick',
        'click .comment_delete': '_onDeleteCommentClick',
        'click .js_close_intro': '_onCloseIntroClick',
    },

    /**
     * @override
     */
    start: function () {
        var self = this;

        this.lastsearch = [];

        // float-left class messes up the post layout OPW 769721
        $('span[data-oe-model="forum.post"][data-oe-field="content"]').find('img.float-left').removeClass('float-left');

        // welcome message action button
        var forumLogin = _.string.sprintf('%s/web?redirect=%s',
            window.location.origin,
            escape(window.location.href)
        );
        $('.forum_register_url').attr('href', forumLogin);

        // Initialize forum's tooltips
        this.$('[data-toggle="tooltip"]').tooltip({delay: 0});
        this.$('[data-toggle="popover"]').popover({offset: 8});

        $('input.js_select2').select2({
            tags: true,
            tokenSeparators: [',', ' ', '_'],
            maximumInputLength: 35,
            minimumInputLength: 2,
            maximumSelectionSize: 5,
            lastsearch: [],
            createSearchChoice: function (term) {
                if (_.filter(self.lastsearch, function (s) {
                    return s.text.localeCompare(term) === 0;
                }).length === 0) {
                    //check Karma
                    if (parseInt($('#karma').val()) >= parseInt($('#karma_edit_retag').val())) {
                        return {
                            id: '_' + $.trim(term),
                            text: $.trim(term) + ' *',
                            isNew: true,
                        };
                    }
                }
            },
            formatResult: function (term) {
                if (term.isNew) {
                    return '<span class="badge badge-primary">New</span> ' + _.escape(term.text);
                } else {
                    return _.escape(term.text);
                }
            },
            ajax: {
                url: '/forum/get_tags',
                dataType: 'json',
                data: function (term) {
                    return {
                        query: term,
                        limit: 50,
                    };
                },
                results: function (data) {
                    var ret = [];
                    _.each(data, function (x) {
                        ret.push({
                            id: x.id,
                            text: x.name,
                            isNew: false,
                        });
                    });
                    self.lastsearch = ret;
                    return {results: ret};
                }
            },
            // Take default tags from the input value
            initSelection: function (element, callback) {
                var data = [];
                _.each(element.data('init-value'), function (x) {
                    data.push({id: x.id, text: x.name, isNew: false});
                });
                element.val('');
                callback(data);
            },
        });

        _.each($('textarea.o_wysiwyg_loader'), function (textarea) {
            var $textarea = $(textarea);
            var editorKarma = $textarea.data('karma') || 0; // default value for backward compatibility
            var $form = $textarea.closest('form');
            var hasFullEdit = parseInt($("#karma").val()) >= editorKarma;
            var toolbar = [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
            ];
            if (hasFullEdit) {
                toolbar.push(['insert', ['linkPlugin', 'mediaPlugin']]);
            }
            toolbar.push(['history', ['undo', 'redo']]);

            var options = {
                height: 200,
                minHeight: 80,
                toolbar: toolbar,
                styleWithSpan: false,
                styleTags: _.without(weDefaultOptions.styleTags, 'h1', 'h2', 'h3'),
                recordInfo: {
                    context: self._getContext(),
                    res_model: 'forum.post',
                    res_id: +window.location.pathname.split('-').pop(),
                },
            };
            if (!hasFullEdit) {
                options.plugins = {
                    LinkPlugin: false,
                    MediaPlugin: false,
                };
            }
            wysiwygLoader.load(self, $textarea[0], options).then(wysiwyg => {
                // float-left class messes up the post layout OPW 769721
                $form.find('.note-editable').find('img.float-left').removeClass('float-left');
                $form.on('click', 'button .a-submit', () => {
                    wysiwyg.save();
                });
            });
        });

        _.each(this.$('.o_wforum_bio_popover'), authorBox => {
            $(authorBox).popover({
                trigger: 'hover',
                offset: 10,
                animation: false,
                html: true,
            });
        });

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onKarmaRequiredClick: function (ev) {
        var $karma = $(ev.currentTarget);
        var karma = $karma.data('karma');
        var forum_id = $('#wrapwrap').data('forum_id');
        if (!karma) {
            return;
        }
        ev.preventDefault();
        var msg = karma + ' ' + _t("karma is required to perform this action. ");
        var title = _t("Karma Error");
        if (forum_id) {
            msg += '<a class="alert-link" href="/forum/' + forum_id + '/faq">' + _t("Read the guidelines to know how to gain karma.") + '</a>';
        }
        if (session.is_website_user) {
            msg = _t("Sorry you must be logged in to perform this action");
            title = _t("Access Denied");
        }
        this.call('crash_manager', 'show_warning', {
            message: msg,
            title: title,
        }, {
            sticky: false,
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onTagFollowBoxMouseEnter: function (ev) {
        $(ev.currentTarget).find('.o_forum_tag_follow_box').stop().fadeIn().css('display', 'block');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onTagFollowBoxMouseLeave: function (ev) {
        $(ev.currentTarget).find('.o_forum_tag_follow_box').stop().fadeOut().css('display', 'none');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onUserInfoMouseEnter: function (ev) {
        $(ev.currentTarget).parent().find('.o_forum_user_bio_expand').delay(500).toggle('fast');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onUserInfoMouseLeave: function (ev) {
        $(ev.currentTarget).parent().find('.o_forum_user_bio_expand').clearQueue();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onUserBioExpandMouseLeave: function (ev) {
        $(ev.currentTarget).fadeOut('fast');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onFlagAlertClick: function (ev) {
        var self = this;
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        this._rpc({
            route: $link.data('href') || ($link.attr('href') !== '#' && $link.attr('href')) || $link.closest('form').attr('action'),
        }).then(function (data) {
            if (data.error) {
                var message;
                if (data.error === 'anonymous_user') {
                    message = _t("Sorry you must be logged to flag a post");
                } else if (data.error === 'post_already_flagged') {
                    message = _t("This post is already flagged");
                } else if (data.error === 'post_non_flaggable') {
                    message = _t("This post can not be flagged");
                }
                self.call('crash_manager', 'show_warning', {
                    message: message,
                    title: _t("Access Denied"),
                }, {
                    sticky: false,
                });
            } else if (data.success) {
                var elem = $link;
                if (data.success === 'post_flagged_moderator') {
                    elem.data('href') && elem.html(' Flagged');
                    var c = parseInt($('#count_flagged_posts').html(), 10);
                    c++;
                    $('#count_flagged_posts').html(c);
                } else if (data.success === 'post_flagged_non_moderator') {
                    elem.data('href') && elem.html(' Flagged');
                    var forumAnswer = elem.closest('.forum_answer');
                    forumAnswer.fadeIn(1000);
                    forumAnswer.slideUp(1000);
                }
            }
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onVotePostClick: function (ev) {
        var self = this;
        ev.preventDefault();
        var $btn = $(ev.currentTarget);
        this._rpc({
            route: $btn.data('href'),
        }).then(function (data) {
            if (data.error) {
                var message;
                if (data.error === 'own_post') {
                    message = _t('Sorry, you cannot vote for your own posts');
                } else if (data.error === 'anonymous_user') {
                    message = _t('Sorry you must be logged to vote');
                }
                self.call('crash_manager', 'show_warning', {
                    message: message,
                    title: _t("Access Denied"),
                }, {
                    sticky: false,
                });
            } else {
                var $container = $btn.closest('.vote');
                var $items = $container.children();
                var $voteUp = $items.filter('.vote_up');
                var $voteDown = $items.filter('.vote_down');
                var $voteCount = $items.filter('.vote_count');
                var userVote = parseInt(data['user_vote']);

                $voteUp.prop('disabled', userVote === 1);
                $voteDown.prop('disabled', userVote === -1);

                $items.removeClass('text-success text-danger text-muted o_forum_vote_animate');
                void $container[0].offsetWidth; // Force a refresh

                if (userVote === 1) {
                    $voteUp.addClass('text-success');
                    $voteCount.addClass('text-success');
                }
                if (userVote === -1) {
                    $voteDown.addClass('text-danger');
                    $voteCount.addClass('text-danger');
                }
                $voteCount.html(data['vote_count']).addClass('o_forum_vote_animate');
            }
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onValidationQueueClick: function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        $link.parents('.post_to_validate').hide();
        $.get($link.attr('href')).then(() => {
            var left = $('.o_js_validation_queue:visible').length;
            var type = $('h2.o_page_header a.active').data('type');
            $('#count_post').text(left);
            $('#moderation_tools a[href*="/' + type + '_"]').find('strong').text(left);
            if (!left) {
                this.$('.o_caught_up_alert').removeClass('d-none');
            }
        }, function () {
            $link.parents('.o_js_validation_queue > div').addClass('bg-danger text-white').css('background-color', '#FAA');
            $link.parents('.post_to_validate').show();
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onAcceptAnswerClick: function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var target = $link.data('target');

        this._rpc({
            route: $link.data('href'),
        }).then(data => {
            if (data.error) {
                if (data.error === 'anonymous_user') {
                    var message = _t("Sorry, anonymous users cannot choose correct answer.");
                }
                this.call('crash_manager', 'show_warning', {
                    message: message,
                    title: _t("Access Denied"),
                }, {
                    sticky: false,
                });
            } else {
                _.each(this.$('.forum_answer'), answer => {
                    var $answer = $(answer);
                    var isCorrect = $answer.is(target) ? data : false;
                    var $toggler = $answer.find('.o_wforum_validate_toggler');
                    var newHelper = isCorrect ? $toggler.data('helper-decline') : $toggler.data('helper-accept');

                    $answer.toggleClass('o_wforum_answer_correct', isCorrect);
                    $toggler.tooltip('dispose')
                            .attr('data-original-title', newHelper)
                            .tooltip({delay: 0});
                });
            }
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onFavoriteQuestionClick: function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        this._rpc({
            route: $link.data('href'),
        }).then(function (data) {
            $link.toggleClass('o_wforum_gold fa-star', data)
                 .toggleClass('fa-star-o text-muted', !data);
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onDeleteCommentClick: function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $container = $link.closest('.o_wforum_post_comments_container');

        this._rpc({
            route: $link.closest('form').attr('action'),
        }).then(function () {
            $link.closest('.o_wforum_post_comment').remove();

            var count = $container.find('.o_wforum_post_comment').length;
            if (count) {
                $container.find('.o_wforum_comments_count').text(count);
            } else {
                $container.find('.o_wforum_comments_count_header').remove();
            }
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onCloseIntroClick: function (ev) {
        ev.preventDefault();
        document.cookie = 'forum_welcome_message = false';
        $('.forum_intro').slideUp();
        return true;
    },
});

publicWidget.registry.websiteForumSpam = publicWidget.Widget.extend({
    selector: '.o_wforum_moderation_queue',
    xmlDependencies: ['/website_forum/static/src/xml/website_forum_share_templates.xml'],
    events: {
        'click .o_wforum_select_all_spam': '_onSelectallSpamClick',
        'click .o_wforum_mark_spam': 'async _onMarkSpamClick',
        'input #spamSearch': '_onSpamSearchInput',
    },

    /**
     * @override
     */
    start: function () {
        this.spamIDs = this.$('.modal').data('spam-ids');
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onSelectallSpamClick: function (ev) {
        var $spamInput = this.$('.modal .tab-pane.active input');
        $spamInput.prop('checked', true);
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onSpamSearchInput: function (ev) {
        var self = this;
        var toSearch = $(ev.currentTarget).val();
        return this._rpc({
            model: 'forum.post',
            method: 'search_read',
            args: [
                [['id', 'in', self.spamIDs],
                    '|',
                    ['name', 'ilike', toSearch],
                    ['content', 'ilike', toSearch]],
                ['name', 'content']
            ],
            kwargs: {}
        }).then(function (o) {
            _.each(o, function (r) {
                r.content = $('<p>' + $(r.content).html() + '</p>').text().substring(0, 250);
            });
            self.$('div.post_spam').html(qweb.render('website_forum.spam_search_name', {
                posts: o,
            }));
        });
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onMarkSpamClick: function (ev) {
        var key = this.$('.modal .tab-pane.active').data('key');
        var $inputs = this.$('.modal .tab-pane.active input.custom-control-input:checked');
        var values = _.map($inputs, function (o) {
            return parseInt(o.value);
        });
        return this._rpc({model: 'forum.post',
            method: 'mark_as_offensive_batch',
            args: [this.spamIDs, key, values],
        }).then(function () {
            window.location.reload();
        });
    },
});

});
