odoo.define('website_forum.website_forum', function (require) {
'use strict';

var core = require('web.core');
var Wysiwyg = require('web_editor.wysiwyg.root');
var publicWidget = require('web.public.widget');
var session = require('web.session');
var utils = require('web.utils');
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
        'click .accept_answer:not(.karma_required)': '_onAcceptAnswerClick',
        'click .validate_answer [data-href]': '_onAcceptAnswerClick',
        'mouseenter .validate_answer [data-href]': '_onRemoveValidAnswerMouse',
        'mouseleave .validate_answer [data-href]': '_onRemoveValidAnswerMouse',
        'click .favourite_question': '_onFavoriteQuestionClick',
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

        _.each($('textarea.load_editor'), function (textarea) {
            var $textarea = $(textarea);
            var editorKarma = $textarea.data('karma') || 0; // default value for backward compatibility
            if (!$textarea.val().match(/\S/)) {
                $textarea.val('<p><br/></p>');
            }
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
                height: 150,
                toolbar: toolbar,
                styleWithSpan: false,
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
            var wysiwyg = new Wysiwyg(self, options);
            wysiwyg.attachTo($textarea).then(function () {
                // float-left class messes up the post layout OPW 769721
                $form.find('.note-editable').find('img.float-left').removeClass('float-left');
                $form.on('click', 'button .a-submit', function () {
                    $form.find('textarea').data('wysiwyg').save();
                });
            });
        });

        // Check all answer status to add text-success on answer if needed
        _.each($('.accept_answer'), function (el) {
            var $el = $(el);
            if ($el.hasClass('oe_answer_true')) {
                $el.addClass('text-success');
            }
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
        var $link = $(ev.currentTarget);
        this._rpc({
            route: $link.data('href'),
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
                $link.parent().find('.vote_count').html(data.vote_count);
                if (data.user_vote === 0) {
                    $link.parent().find('.text-success').removeClass('text-success');
                    $link.parent().find('.text-warning').removeClass('text-warning');
                } else {
                    if (data.user_vote === 1) {
                        $link.addClass('text-success');
                    } else {
                        $link.addClass('text-warning');
                    }
                }
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
        $.get($link.attr('href')).then(function () {
            var left = $('.o_js_validation_queue:visible').length;
            var type = $('h2.o_page_header a.active').data('type');
            $('#count_post').text(left);
            $('#moderation_tools a[href*="/' + type + '_"]').find('strong').text(left);
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
        var self = this;
        ev.preventDefault();
        var self = this;
        var $acceptAnswerLinks = this.$('.accept_answer');
        var $link = $(ev.currentTarget);
        this._rpc({
            route: $link.data('href'),
        }).then(function (data) {
            if (data.error) {
                if (data.error === 'anonymous_user') {
                    var message = _t("Sorry, anonymous users cannot choose correct answer.");
                }
                self.call('crash_manager', 'show_warning', {
                    message: message,
                    title: _t("Access Denied"),
                }, {
                    sticky: false,
                });
            } else {
                $acceptAnswerLinks.removeClass('oe_answer_true')
                                  .addClass('oe_answer_false');
                $link.toggleClass('oe_answer_true', !!data)
                     .toggleClass('oe_answer_false', !data);

                // TODO in master, review the utility of this function...
                self._onCheckAnswerStatus(ev);

                // If we are removing an accepted answer, reload the page as the
                // design is quite different with or without an accepted answer.
                if ($link.closest('.validate_answer').length) {
                    window.location.reload();
                }
            }
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onRemoveValidAnswerMouse: function (ev) {
        var hover = (ev.type === 'mouseenter');
        $(ev.currentTarget).find('.fa')
            .toggleClass('fa-times-circle text-danger', hover)
            .toggleClass('fa-check-circle text-success', !hover);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onCheckAnswerStatus: function (ev) {
        _.each(this.$('.accept_answer'), function (link) {
            var $link = $(link);
            $link.toggleClass('text-success', $link.hasClass('oe_answer_true'));
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
            $link.toggleClass('forum_favourite_question', !!data);
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onDeleteCommentClick: function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        this._rpc({
            route: $link.closest('form').attr('action'),
        }).then(function () {
            $link.parents('.comment').first().remove();
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
