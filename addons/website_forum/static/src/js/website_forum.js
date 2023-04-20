/** @odoo-module **/

import dom from "web.dom";
import core from "web.core";
import {setCookie} from "web.utils.cookies";
import Dialog from "web.Dialog";
import wysiwygLoader from "web_editor.loader";
import publicWidget from "web.public.widget";
import { Markup } from "web.utils";
import session from "web.session";
import { escape } from "@web/core/utils/strings";
var qweb = core.qweb;

var _t = core._t;

publicWidget.registry.websiteForum = publicWidget.Widget.extend({
    selector: '.website_forum',
    events: {
        'click .karma_required': '_onKarmaRequiredClick',
        'mouseenter .o_js_forum_tag_follow': '_onTagFollowBoxMouseEnter',
        'mouseleave .o_js_forum_tag_follow': '_onTagFollowBoxMouseLeave',
        'mouseenter .o_forum_user_info': '_onUserInfoMouseEnter',
        'mouseleave .o_forum_user_info': '_onUserInfoMouseLeave',
        'mouseleave .o_forum_user_bio_expand': '_onUserBioExpandMouseLeave',
        'click .o_wforum_flag:not(.karma_required)': '_onFlagAlertClick',
        'click .o_wforum_flag_validator': '_onFlagValidatorClick',
        'click .o_wforum_flag_mark_as_offensive': '_onFlagMarkAsOffensiveClick',
        'click .vote_up:not(.karma_required), .vote_down:not(.karma_required)': '_onVotePostClick',
        'click .o_js_validation_queue a[href*="/validate"]': '_onValidationQueueClick',
        'click .o_wforum_validate_toggler:not(.karma_required)': '_onAcceptAnswerClick',
        'click .o_wforum_favourite_toggle': '_onFavoriteQuestionClick',
        'click .comment_delete': '_onDeleteCommentClick',
        'click .js_close_intro': '_onCloseIntroClick',
        'submit .js_wforum_submit_form:has(:not(.karma_required).o_wforum_submit_post)': '_onSubmitForm',
    },

    /**
     * @override
     */
    start: function () {
        var self = this;

        this.lastsearch = [];

        // float-start class messes up the post layout OPW 769721
        $('span[data-oe-model="forum.post"][data-oe-field="content"]').find('img.float-start').removeClass('float-start');

        // welcome message action button
        var forumLogin = _.string.sprintf('%s/web?redirect=%s',
            window.location.origin,
            encodeURIComponent(window.location.href)
        );
        $('.forum_register_url').attr('href', forumLogin);

        // Initialize forum's tooltips
        this.$('[data-bs-toggle="tooltip"]').tooltip({delay: 0});
        this.$('[data-bs-toggle="popover"]').popover({offset: 8});

        $('input.js_select2').select2({
            tags: true,
            tokenSeparators: [',', ' ', '_'],
            maximumInputLength: 35,
            minimumInputLength: 2,
            maximumSelectionSize: 5,
            lastsearch: [],
            createSearchChoice: function (term) {
                if (self.lastsearch.filter(s => s.text.localeCompare(term) === 0).length === 0) {
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
                    return '<span class="badge bg-primary">New</span> ' + escape(term.text);
                } else {
                    return escape(term.text);
                }
            },
            ajax: {
                url: '/forum/get_tags',
                dataType: 'json',
                data: function (term) {
                    return {
                        query: term,
                        limit: 50,
                        forum_id: $('#wrapwrap').data('forum_id'),
                    };
                },
                results: function (data) {
                    var ret = [];
                    data.forEach((x) => {
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
                element.data("init-value").forEach((x) => {
                    data.push({id: x.id, text: x.name, isNew: false});
                });
                element.val('');
                callback(data);
            },
        });

        $('textarea.o_wysiwyg_loader').toArray().forEach((textarea) => {
            var $textarea = $(textarea);
            var editorKarma = $textarea.data('karma') || 0; // default value for backward compatibility
            var $form = $textarea.closest('form');
            var hasFullEdit = parseInt($("#karma").val()) >= editorKarma;

            var options = {
                toolbarTemplate: 'website_forum.web_editor_toolbar',
                recordInfo: {
                    context: self._getContext(),
                    res_model: 'forum.post',
                    // Id is retrieved from URL, which is either:
                    // - /forum/name-1/post/something-5
                    // - /forum/name-1/post/something-5/edit
                    // TODO: Make this more robust.
                    res_id: +window.location.pathname.split('-').slice(-1)[0].split('/')[0],
                },
                resizable: true,
                userGeneratedContent: true,
            };
            options.allowCommandLink = hasFullEdit;
            options.allowCommandImage = hasFullEdit;
            wysiwygLoader.loadFromTextarea(self, $textarea[0], options).then(wysiwyg => {
                if (!hasFullEdit) {
                    wysiwyg.toolbar.$el.find('#link, #media').remove();
                }
                // float-start class messes up the post layout OPW 769721
                $form.find('.note-editable').find('img.float-start').removeClass('float-start');
            });
        });

        this.$('.o_wforum_bio_popover').toArray().forEach((authorBox) => {
            $(authorBox).popover({
                trigger: 'hover',
                offset: '10',
                animation: false,
                html: true,
                customClass: 'o_wforum_bio_popover_container',
            });
        });

        this.$('#post_reply').on('shown.bs.collapse', function (e) {
            const replyEl = document.querySelector('#post_reply');
            const scrollingElement = dom.closestScrollable(replyEl.parentNode);
            dom.scrollTo(replyEl, {
                forcedOffset: $(scrollingElement).innerHeight() - $(replyEl).innerHeight(),
            });
        });

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     *
     * @override
     * @param {Event} ev
     */
    _onSubmitForm: function (ev) {
        let validForm = true;

        let $form = $(ev.currentTarget);
        let $title = $form.find('input[name=post_name]');
        let $textarea = $form.find('textarea[name=content]');
        // It's not really in the textarea that the user write at first
        let textareaContent = $form.find('.o_wysiwyg_textarea_wrapper').text().trim();

        if ($title.length && $title[0].required) {
            if ($title.val()) {
                $title.removeClass('is-invalid');
            } else {
                $title.addClass('is-invalid');
                validForm = false;
            }
        }

        // Because the textarea is hidden, we add the red or green border to its container
        if ($textarea[0] && $textarea[0].required) {
            let $textareaContainer = $form.find('.o_wysiwyg_textarea_wrapper');
            if (!textareaContent.length) {
                $textareaContainer.addClass('border border-danger rounded-top');
                validForm = false;
            } else {
                $textareaContainer.removeClass('border border-danger rounded-top');
            }
        }

        if (validForm) {
            // Stores social share data to display modal on next page.
            if ($form.has('.oe_social_share_call').length) {
                sessionStorage.setItem('social_share', JSON.stringify({
                    targetType: $(ev.currentTarget).find('.o_wforum_submit_post').data('social-target-type'),
                }));
            }
        } else {
            ev.preventDefault();
            setTimeout(function() {
                var $buttons = $(ev.currentTarget).find('button[type="submit"], a.a-submit');
                $buttons.toArray().forEach((btn) => {
                    let $btn = $(btn);
                    $btn.find('i').remove();
                    $btn.prop('disabled', false);
                });
            }, 0);
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onKarmaRequiredClick: function (ev) {
        const karma = parseInt(ev.currentTarget.dataset.karma);
        if (!karma) {
            return;
        }

        ev.preventDefault();
        const forumID = parseInt(document.getElementById('wrapwrap').dataset.forum_id);
        const notifOptions = {
            type: "warning",
            sticky: false,
        };
        if (session.is_website_user) {
            notifOptions.title = _t("Access Denied");
            notifOptions.message = _t("Sorry you must be logged in to perform this action");
        } else {
            notifOptions.title = _t("Karma Error");
            // FIXME this translation is bad, the number should be part of the
            // translation, to fix in the appropriate version
            notifOptions.message = `${karma} ${_t("karma is required to perform this action. ")}`;
            if (forumID) {
                const linkLabel = _t("Read the guidelines to know how to gain karma.");
                notifOptions.message = Markup`
                    ${notifOptions.message}<br/>
                    <a class="alert-link" href="/forum/${encodeURIComponent(forumID)}/faq">${linkLabel}</a>
                `;
            }
        }
        this.displayNotification(notifOptions);
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
        ev.preventDefault();
        const elem = ev.currentTarget;
        this._rpc({
            route: elem.dataset.href || (elem.getAttribute('href') !== '#' && elem.getAttribute('href')) || elem.closest('form').getAttribute('action'),
        }).then(data => {
            if (data.error) {
                var message;
                if (data.error === 'anonymous_user') {
                    message = _t("Sorry you must be logged to flag a post");
                } else if (data.error === 'post_already_flagged') {
                    message = _t("This post is already flagged");
                } else if (data.error === 'post_non_flaggable') {
                    message = _t("This post can not be flagged");
                }
                this.displayNotification({
                    message: message,
                    title: _t("Access Denied"),
                    sticky: false,
                    type: "warning",
                });
            } else if (data.success) {
                const child = elem.firstElementChild;
                if (data.success === 'post_flagged_moderator') {
                    const countFlaggedPosts = this.el.querySelector('#count_flagged_posts');
                    elem.innerText = _t(' Flagged');
                    elem.prepend(child);
                    if (countFlaggedPosts) {
                        countFlaggedPosts.classList.remove('bg-light');
                        countFlaggedPosts.classList.add('bg-danger');
                        countFlaggedPosts.innerText = parseInt(countFlaggedPosts.innerText, 10) + 1;
                    }
                    $(elem).nextAll('.flag_validator').removeClass('d-none');
                } else if (data.success === 'post_flagged_non_moderator') {
                    const forumAnswer = elem.closest('.forum_answer');
                    elem.innerText = _t(' Flagged');
                    elem.prepend(child);
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
        var $btn = $(ev.currentTarget);
        this._rpc({
            route: $btn.data('href'),
        }).then(data => {
            if (data.error) {
                var message;
                if (data.error === 'own_post') {
                    message = _t('Sorry, you cannot vote for your own posts');
                } else if (data.error === 'anonymous_user') {
                    message = _t('Sorry you must be logged to vote');
                }
                this.displayNotification({
                    message: message,
                    title: _t("Access Denied"),
                    sticky: false,
                    type: "warning",
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
                    $voteDown.removeClass('karma_required');
                }
                if (userVote === -1) {
                    $voteDown.addClass('text-danger');
                    $voteCount.addClass('text-danger');
                    $voteUp.removeClass('karma_required');
                }
                if (userVote === 0) {
                    if (!$voteDown.data('can-downvote')) {
                        $voteDown.addClass('karma_required');
                    }
                    if (!$voteUp.data('can-upvote')) {
                        $voteUp.addClass('karma_required');
                    }
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
                this.displayNotification({
                    message: message,
                    title: _t("Access Denied"),
                    sticky: false,
                    type: "warning",
                });
            } else {
                this.$('.forum_answer').toArray().forEach((answer) => {
                    var $answer = $(answer);
                    var isCorrect = $answer.is(target) ? data : false;
                    var $toggler = $answer.find('.o_wforum_validate_toggler');
                    var newHelper = isCorrect ? $toggler.data('helper-decline') : $toggler.data('helper-accept');

                    $answer.toggleClass('o_wforum_answer_correct', isCorrect);
                    $toggler.tooltip('dispose')
                            .attr('data-bs-original-title', newHelper)
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
        setCookie('forum_welcome_message', false, 24 * 60 * 60 * 365, 'optional');
        $('.forum_intro').slideUp();
        return true;
    },
    /**
     * @private
     * @param {Event} ev
     */
    async _onFlagValidatorClick(ev) {
        ev.preventDefault();
        const currentTarget = ev.currentTarget;
        await this._rpc({
            model: 'forum.post',
            method: currentTarget.dataset.action,
            args: [parseInt(currentTarget.dataset.postId)],
        });
        currentTarget.parentElement.querySelectorAll('.flag_validator').forEach((element) => element.classList.toggle('d-none'));
        const flaggedButton = currentTarget.parentElement.firstElementChild,
            child = flaggedButton.firstElementChild,
            countFlaggedPosts = this.el.querySelector('#count_flagged_posts'),
            count = parseInt(countFlaggedPosts.innerText, 10) - 1;

        flaggedButton.innerText = _t(' Flag');
        flaggedButton.prepend(child);
        if (count === 0) {
            countFlaggedPosts.classList.add("bg-light");
        }
        countFlaggedPosts.innerText = count;
    },
    /**
     * @private
     * @param {Event} ev
     */
    async _onFlagMarkAsOffensiveClick(ev) {
        ev.preventDefault();
        const template = await this._rpc({
            route: $(ev.currentTarget).data('action'),
        });
        const dialog = new Dialog(this, {
            size: 'medium',
            title: _t("Offensive Post"),
            $content: template,
            renderFooter: false,
        }).open();
        dialog.opened().then(() => {
            dialog.$(".btn-light:contains('Discard')").click((ev) => {
                ev.preventDefault();
                dialog.close();
            });
        });
    },
});

publicWidget.registry.websiteForumSpam = publicWidget.Widget.extend({
    selector: '.o_wforum_moderation_queue',
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
            Object.values(o).forEach((r) => {
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
        var $inputs = this.$('.modal .tab-pane.active input.form-check-input:checked');
        var values = $inputs.map((o) => parseInt(o.value));
        return this._rpc({model: 'forum.post',
            method: 'mark_as_offensive_batch',
            args: [this.spamIDs, key, values],
        }).then(function () {
            window.location.reload();
        });
    },
});

publicWidget.registry.WebsiteForumBackButton = publicWidget.Widget.extend({
    selector: '.o_back_button',
    events: {
        'click': '_onBackButtonClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onBackButtonClick() {
        window.history.back();
    },
});
