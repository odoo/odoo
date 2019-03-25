odoo.define('website_forum.website_forum', function (require) {
'use strict';

var core = require('web.core');
var Wysiwyg = require('web_editor.wysiwyg.root');
var publicWidget = require('web.public.widget');
var session = require('web.session');
var qweb = core.qweb;
var WebsiteProfile = require('website_profile.website_profile');

var _t = core._t;

publicWidget.registry.websiteForum = publicWidget.Widget.extend({
    selector: '.website_forum',
    xmlDependencies: ['/website_forum/static/src/xml/website_forum_share_templates.xml'],
    events: {
        'click .karma_required': '_onKarmaRequiredClick',
        'mouseenter .o_js_forum_tag_follow': '_onTagFollowBoxMouseEnter',
        'mouseleave .o_js_forum_tag_follow': '_onTagFollowBoxMouseLeave',
        'click .o_forum_profile_pic_edit': '_onEditProfilePicClick',
        'change .o_forum_file_upload': '_onFileUploadChange',
        'click .o_forum_profile_pic_clear': '_onProfilePicClearClick',
        'mouseenter .o_forum_user_info': '_onUserInfoMouseEnter',
        'mouseleave .o_forum_user_info': '_onUserInfoMouseLeave',
        'mouseleave .o_forum_user_bio_expand': '_onUserBioExpandMouseLeave',
        'click .flag:not(.karma_required)': '_onFlagAlertClick',
        'click .vote_up:not(.karma_required), .vote_down:not(.karma_required)': '_onVotePostClick',
        'click .o_js_validation_queue a[href*="/validate"]': '_onValidationQueueClick',
        'click .accept_answer:not(.karma_required)': '_onAcceptAnswerClick',
        'click .favourite_question': '_onFavoriteQuestionClick',
        'click .comment_delete': '_onDeleteCommentClick',
        'click .notification_close': '_onCloseNotificationClick',
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
            var editorKarma = $textarea.data('karma') || 30; // default value for backward compatibility
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
                $form.on('click', 'button, .a-submit', function () {
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
        if (!karma) {
            return;
        }
        ev.preventDefault();
        var msg = karma + ' ' + _t("karma is required to perform this action. You can earn karma by having your answers upvoted by the community.");
        if (session.is_website_user) {
            msg = _t("Sorry you must be logged in to perform this action");
        }
        var $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="karma_alert">' +
            '<button type="button" class="close notification_close" data-dismiss="alert">&times;</button>' +
            msg + '</div>');
        var $voteAlert = $('#karma_alert');
        if ($voteAlert.length) {
            $voteAlert.remove();
        }
        $karma.after($warning);
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
    _onEditProfilePicClick: function (ev) {
        ev.preventDefault();
        $(ev.currentTarget).closest('form').find('.o_forum_file_upload').trigger('click');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onFileUploadChange: function (ev) {
        if (!ev.currentTarget.files.length) {
            return;
        }
        var $form = $(ev.currentTarget).closest('form');
        var reader = new window.FileReader();
        reader.onload = function (ev) {
            $form.find('.o_forum_avatar_img').attr('src', ev.target.result);
        };
        reader.readAsDataURL(ev.currentTarget.files[0]);
        $form.find('#forum_clear_image').remove();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onProfilePicClearClick: function (ev) {
        var $form = $(ev.currentTarget).closest('form');
        $form.find('.o_forum_avatar_img').attr('src', '/web/static/src/img/placeholder.png');
        $form.append($('<input/>', {
            name: 'clear_image',
            id: 'forum_clear_image',
            type: 'hidden',
        }));
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
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        this._rpc({
            route: $link.data('href') || ($link.attr('href') !== '#' && $link.attr('href')) || $link.closest('form').attr('action'),
        }).then(function (data) {
            if (data.error) {
                var $warning;
                if (data.error === 'anonymous_user') {
                    $warning = $(
                        '<div class="alert alert-danger alert-dismissable oe_forum_alert" id="flag_alert">' +
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>' +
                            _t("Sorry you must be logged to flag a post") +
                        '</div>'
                    );
                } else if (data.error === 'post_already_flagged') {
                    $warning = $(
                        '<div class="alert alert-danger alert-dismissable oe_forum_alert" id="flag_alert">' +
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>' +
                            _t("This post is already flagged") +
                            '<button type="button" class="close notification_close" t-att-id="notification.id" data-dismiss="alert" aria-label="Close">&times;</button>' +
                        '</div>'
                    );
                } else if (data.error === 'post_non_flaggable') {
                    $warning = $(
                        '<div class="alert alert-danger alert-dismissable oe_forum_alert" id="flag_alert">' +
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>' +
                            _t("This post can not be flagged") +
                            '<button type="button" class="close notification_close" t-att-id="notification.id" data-dismiss="alert" aria-label="Close">&times;</button>' +
                        '</div>'
                    );
                }
                var $flagAlert = $link.parent().find('#flag_alert');
                if ($flagAlert.length === 0) {
                    $link.parent().append($warning);
                }
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
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        this._rpc({
            route: $link.data('href'),
        }).then(function (data) {
            if (data.error) {
                var $warning;
                if (data.error === 'own_post') {
                    $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="vote_alert">' +
                        '<button type="button" class="close notification_close" data-dismiss="alert">&times;</button>' +
                        _t('Sorry, you cannot vote for your own posts') +
                        '</div>');
                } else if (data.error === 'anonymous_user') {
                    $warning = $('<div class="alert alert-danger alert-dismissable oe_forum_alert" id="vote_alert">' +
                        '<button type="button" class="close notification_close" data-dismiss="alert">&times;</button>' +
                        _t('Sorry you must be logged to vote') +
                        '</div>');
                }
                var $voteAlert = $link.parent().find('#vote_alert');
                if ($voteAlert.length === 0) {
                    $link.parent().append($warning);
                }
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
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        this._rpc({
            route: $link.data('href'),
        }).then(function (data) {
            if (data.error) {
                if (data.error === 'anonymous_user') {
                    var $warning = $(
                        '<div class="alert alert-danger alert-dismissable" id="correct_answer_alert" style="position:absolute; margin-top: -30px; margin-left: 90px;">' +
                            '<button type="button" class="close notification_close" data-dismiss="alert" aria-hidden="true">&times;</button>' +
                            _t("Sorry, anonymous users cannot choose correct answer.") +
                        '</div>'
                    );
                }
                var $correctAnswerAlert = $link.parent().find('#correct_answer_alert');
                if ($correctAnswerAlert.length === 0) {
                    $link.parent().append($warning);
                }
            } else {
                $link.toggleClass('oe_answer_true', !!data)
                     .toggleClass('oe_answer_false', !data);
            }
        });
        this._onCheckAnswerStatus(ev);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onCheckAnswerStatus: function (ev) {
        var $link = $(ev.currentTarget);
        $link.toggleClass('text-success', !$link.hasClass('oe_answer_true'));
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
    _onCloseNotificationClick: function (ev) {
        if (!session.is_website_user) {
            ev.preventDefault();
            var $link = $(ev.currentTarget);
            this._rpc({
                route: '/forum/notification_read',
                params: {
                    notification_id: $link.attr('id'),
                },
            });
        }
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
