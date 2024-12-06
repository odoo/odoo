/** @odoo-module **/

import { markup } from "@odoo/owl";
import { FlagMarkAsOffensiveDialog } from "../components/flag_mark_as_offensive/flag_mark_as_offensive";
import dom from "@web/legacy/js/core/dom";
import { cookie } from "@web/core/browser/cookie";;
import { loadWysiwygFromTextarea } from "@web_editor/js/frontend/loadWysiwygFromTextarea";
import publicWidget from "@web/legacy/js/public/public_widget";
import { session } from "@web/session";
import { escape } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

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
        'click .o_wforum_validation_queue a[href*="/validate"]': '_onValidationQueueClick',
        'click .o_wforum_validate_toggler:not(.karma_required)': '_onAcceptAnswerClick',
        'click .o_wforum_favourite_toggle': '_onFavoriteQuestionClick',
        'click .comment_delete:not(.karma_required)': '_onDeleteCommentClick',
        'click .js_close_intro': '_onCloseIntroClick',
        'click .answer_collapse': '_onExpandAnswerClick',
        'submit .js_wforum_submit_form:has(:not(.karma_required).o_wforum_submit_post)': '_onSubmitForm',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
        this.orm = this.bindService("orm");
        this.notification = this.bindService("notification");
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
        var forumLogin = `${window.location.origin}/web?redirect=${encodeURIComponent(window.location.href)}`
        $('.forum_register_url').attr('href', forumLogin);

        // Initialize forum's tooltips
        this.$('[data-bs-toggle="tooltip"]').tooltip({delay: 0});
        this.$('[data-bs-toggle="popover"]').popover({offset: '8'});

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

        $('textarea.o_wysiwyg_loader').toArray().forEach(async (textarea) => {
            var $textarea = $(textarea);
            var editorKarma = $textarea.data('karma') || 0; // default value for backward compatibility
            var $form = $textarea.closest('form');
            var hasFullEdit = parseInt($("#karma").val()) >= editorKarma;
            let recordContent = '';
            let resId = 0;
            if (window.location.pathname.includes('edit')) {
                // Id is retrieved from URL, which is either:
                // - /forum/name-1/post/something-5
                // - /forum/name-1/post/something-5/edit
                // TODO: Make this more robust.
                resId = +window.location.pathname.split('-').slice(-1)[0].split('/')[0];
                const data = await this.orm.call("forum.post", "search_read", [], {
                    domain: [['id', '=', resId]],
                    fields: ['content'],
                });
                if (data && data.length) {
                    recordContent = data[0]['content'];
                }
            }
            var options = {
                toolbarTemplate: 'website_forum.web_editor_toolbar',
                toolbarOptions: {
                    showColors: false,
                    showFontSize: false,
                    showHistory: true,
                    showHeading1: false,
                    showHeading2: false,
                    showHeading3: false,
                    showLink: hasFullEdit,
                    showImageEdit: hasFullEdit,
                },
                recordInfo: {
                    context: self._getContext(),
                    res_model: 'forum.post',
                    res_id: resId,
                },
                value: recordContent,
                resizable: true,
                userGeneratedContent: true,
                height: 350,
            };
            options.allowCommandLink = hasFullEdit;
            options.allowCommandImage = hasFullEdit;
            loadWysiwygFromTextarea(self, $textarea[0], options).then(wysiwyg => {
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
                customClass: 'o_wforum_bio_popover_container shadow-sm',
            });
        });

        this.$('#post_reply').on('shown.bs.collapse', function (e) {
            const replyEl = document.querySelector('#post_reply');
            const scrollingElement = $(replyEl.parentNode).closestScrollable()[0];
            dom.scrollTo(replyEl, {
                forcedOffset: $(scrollingElement).innerHeight() - $(replyEl).innerHeight(),
            });
        });
        document.querySelectorAll('.o_wforum_question, .o_wforum_answer, .o_wforum_post_comment, .o_wforum_last_activity')
            .forEach((post) => {
                post.querySelector('.o_wforum_relative_datetime').textContent = luxon.DateTime
                    .fromSQL(post.dataset.lastActivity, {zone: 'utc'})
                    .toRelative();
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
        const fillableTextAreaEl = $form[0].querySelector(".o_wysiwyg_textarea_wrapper");
        const isTextAreaFilled = fillableTextAreaEl &&
            (fillableTextAreaEl.innerText.trim() || fillableTextAreaEl.querySelector("img"));

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
            if (!isTextAreaFilled) {
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
    _onExpandAnswerClick: function (ev) {
        const expandableWindow = ev.currentTarget;
        if (ev.target.matches('.o_wforum_expand_toggle')) {
            expandableWindow.classList.toggle('o_expand')
            expandableWindow.classList.toggle('min-vh-100');
            expandableWindow.classList.toggle('w-lg-50');
        } else if (ev.target.matches('.o_wforum_discard_btn')){
            expandableWindow.classList.remove('o_expand', 'min-vh-100');
            expandableWindow.classList.add('w-lg-50');
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
        if (session.is_website_user) {
            this._displayAccessDeniedNotification(
                markup(`<p>${_t('Oh no! Please <a href="%s">sign in</a> to vote', "/web/login")}</p>`)
            );
            return;
        }
        const forumId = parseInt(document.getElementById('wrapwrap').dataset.forum_id);
        const additionalInfoWithForumID = forumId
            ? markup(`<br/>
                <a class="alert-link" href="/forum/${forumId}/faq">
                    ${_t("Read the guidelines to know how to gain karma.")}
                </a>`)
            : "";
        const translatedText = _t("karma is required to perform this action. ");
        const message = markup(`${karma} ${translatedText}${additionalInfoWithForumID}`);
        this.notification.add(message, {
            type: "warning",
            sticky: false,
            title: _t("Karma Error"),
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
        ev.preventDefault();
        const elem = ev.currentTarget;
        this.rpc(
            elem.dataset.href || (elem.getAttribute('href') !== '#' && elem.getAttribute('href')) || elem.closest('form').getAttribute('action'),
        ).then(data => {
            if (data.error) {
                const message = data.error === 'anonymous_user'
                    ? _t("Sorry you must be logged to flag a post")
                    : data.error === 'post_already_flagged'
                        ? _t("This post is already flagged")
                        : data.error === 'post_non_flaggable'
                            ? _t("This post can not be flagged")
                            : data.error;
                this._displayAccessDeniedNotification(message);
            } else if (data.success) {
                const child = elem.firstElementChild;
                if (data.success === 'post_flagged_moderator') {
                    const countFlaggedPosts = this.el.querySelector('#count_posts_queue_flagged');
                    elem.innerText = _t(' Flagged');
                    elem.prepend(child);
                    if (countFlaggedPosts) {
                        countFlaggedPosts.classList.remove('bg-light');
                        countFlaggedPosts.classList.remove('d-none');
                        countFlaggedPosts.classList.add('bg-danger');
                        countFlaggedPosts.innerText = parseInt(countFlaggedPosts.innerText, 10) + 1;
                    }
                    $(elem).nextAll('.flag_validator').removeClass('d-none');
                } else if (data.success === 'post_flagged_non_moderator') {
                    elem.innerText = _t(' Flagged');
                    elem.prepend(child);
                    const $forumAnswer = $(elem).closest('.o_wforum_answer');
                    if ($forumAnswer) {
                        $forumAnswer.fadeIn(1000);
                        $forumAnswer.slideUp(1000);
                    }
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
        this.rpc($btn.data('href')).then(data => {
            if (data.error) {
                const message = data.error === 'own_post'
                    ? _t('Sorry, you cannot vote for your own posts')
                    : data.error === 'anonymous_user'
                        ? markup(`<p>${_t('Oh no! Please <a href="%s">sign in</a> to vote', "/web/login")}</p>`)
                        : data.error;
                this._displayAccessDeniedNotification(message);
            } else {
                var $container = $btn.closest('.vote');
                var $items = $container.children();
                var $voteUp = $items.filter('.vote_up');
                var $voteDown = $items.filter('.vote_down');
                var $voteCount = $items.filter('.vote_count');
                var userVote = parseInt(data['user_vote']);

                $voteUp.prop('disabled', userVote === 1);
                $voteDown.prop('disabled', userVote === -1);

                $items.removeClass('text-success text-danger text-muted opacity-75 o_forum_vote_animate');
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
                    $voteCount.addClass('text-muted opacity-75');
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
     * Call the route to moderate/validate the post, then hide the validated post
     * and decrement the count in the appropriate queue badge of the sidebar on success.
     *
     * @private
     * @param {Event} ev
     */
    _onValidationQueueClick: async function (ev) {
        ev.preventDefault();
        const approvalLink = ev.currentTarget;
        const postBeingValidated = this._findParent(approvalLink, '.post_to_validate');
        if (!postBeingValidated) {
            return;
        }
        postBeingValidated.classList.add('d-none');
        let ok;
        try {
            ok = (await fetch(approvalLink.href)).ok;
        } catch {
            // Calling the endpoint like this returns an HTML page. As we can't
            // extract the error message from that, we disregard it and simply
            // restore the post's visibility. This __should__ be improved.
        }
        if (!ok) {
            postBeingValidated.classList.remove('d-none');
            return;
        }
        const nbLeftInQueue = Array.from(document.querySelectorAll('.post_to_validate'))
            .filter(e => window.getComputedStyle(e).display !== 'none')
            .length;
        const queueType = document.querySelector('#queue_type').dataset.queueType;
        const queueCountBadge = document.querySelector(`#count_posts_queue_${queueType}`);
        queueCountBadge.innerText = nbLeftInQueue;
        if (!nbLeftInQueue) {
            document.querySelector('.o_caught_up_alert').classList.remove('d-none');
            document.querySelector('.o_wforum_btn_filter_tool')?.classList.add('d-none');
            queueCountBadge.classList.add('d-none');
        }
    },
    _findParent: function (el, selector) {
        while (el.parentElement && !el.matches(selector)) {
            el = el.parentElement;
        }
        return el.matches(selector) ? el : null;
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onAcceptAnswerClick: async function (ev) {
        ev.preventDefault();
        const link = ev.currentTarget;
        const target = link.dataset.target;
        const data = await this.rpc(link.dataset.href);
        if (data.error) {
            const message = data.error === 'anonymous_user'
                ? _t('Sorry, anonymous users cannot choose correct answers.')
                : data.error === 'own_post'
                    ? _t('Sorry, you cannot select your own posts as best answer')
                    : data.error;
            this._displayAccessDeniedNotification(message);
            return;
        }
        for (const answer of document.querySelectorAll('.o_wforum_answer')) {
            const isCorrect = answer.matches(target) ? data : false;
            const toggler = answer.querySelector('.o_wforum_validate_toggler');
            toggler.setAttribute('data-bs-original-title', isCorrect ? toggler.dataset.helperDecline : toggler.dataset.helperAccept);
            const styleForCorrect = isCorrect ? answer.classList.add : answer.classList.remove;
            const styleForIncorrect = isCorrect ? answer.classList.remove : answer.classList.add;
            styleForCorrect.call(answer.classList, 'o_wforum_answer_correct', 'my-2', 'mx-n3', 'mx-lg-n2', 'mx-xl-n3', 'py-3', 'px-3', 'px-lg-2', 'px-xl-3');
            styleForIncorrect.call(toggler.classList, 'opacity-50');
            const answerBorder = answer.querySelector('div .border-start');
            styleForCorrect.call(answerBorder.classList, 'border-success');
            const togglerIcon = toggler.querySelector('.fa');
            styleForCorrect.call(togglerIcon.classList, 'fa-check-circle', 'text-success');
            styleForIncorrect.call(togglerIcon.classList, 'fa-check-circle-o');
            const correctBadge = answer.querySelector('.o_wforum_answer_correct_badge');
            styleForCorrect.call(correctBadge.classList, 'd-inline');
            styleForIncorrect.call(correctBadge.classList, 'd-none');
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onFavoriteQuestionClick: async function (ev) {
        ev.preventDefault();
        const link = ev.currentTarget;
        const data = await this.rpc(link.dataset.href);
        link.classList.toggle('opacity-50', !data);
        link.classList.toggle('opacity-100-hover', !data);
        const link_icon = link.querySelector('.fa');
        link_icon.classList.toggle('fa-star-o', !data);
        link_icon.classList.toggle('o_wforum_gold', data)
        link_icon.classList.toggle('fa-star', data)
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onDeleteCommentClick: function (ev) {
        ev.preventDefault();
        var $link = $(ev.currentTarget);
        var $container = $link.closest('.o_wforum_post_comments_container');

        this.rpc($link.closest('form').attr('action')).then(function () {
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
        cookie.set('forum_welcome_message', false, 24 * 60 * 60 * 365, 'optional');
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
        await this.orm.call("forum.post", currentTarget.dataset.action, [
            parseInt(currentTarget.dataset.postId),
        ]);
        this._findParent(currentTarget, '.o_wforum_flag_alert')?.classList.toggle('d-none');
        const flaggedButton = currentTarget.parentElement.firstElementChild,
            child = flaggedButton.firstElementChild,
            countFlaggedPosts = this.el.querySelector('#count_posts_queue_flagged'),
            count = parseInt(countFlaggedPosts.innerText, 10) - 1;

        flaggedButton.innerText = _t(' Flag');
        flaggedButton.prepend(child);
        if (count === 0) {
            countFlaggedPosts.classList.add('bg-light');
        }
        countFlaggedPosts.innerText = count;
    },
    /**
     * @private
     * @param {Event} ev
     */
    async _onFlagMarkAsOffensiveClick(ev) {
        ev.preventDefault();
        const template = await this.rpc($(ev.currentTarget).data('action'));
        this.call("dialog", "add", FlagMarkAsOffensiveDialog, {
            title: _t("Offensive Post"),
            body: markup(template),
        });
    },
    _displayAccessDeniedNotification(message) {
        this.notification.add(message, {
            title: _t('Access Denied'),
            sticky: false,
            type: 'warning',
        });
    }
});

publicWidget.registry.websiteForumSpam = publicWidget.Widget.extend({
    selector: '.o_wforum_moderation_queue',
    events: {
        'click .o_wforum_select_all_spam': '_onSelectallSpamClick',
        'click .o_wforum_mark_spam': 'async _onMarkSpamClick',
        'input #spamSearch': '_onSpamSearchInput',
    },

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
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
        return this.orm.searchRead(
            "forum.post",
            [['id', 'in', self.spamIDs],
                '|',
                ['name', 'ilike', toSearch],
                ['content', 'ilike', toSearch]],
            ['name', 'content']
        ).then(function (o) {
            Object.values(o).forEach((r) => {
                r.content = $('<p>' + $(r.content).html() + '</p>').text().substring(0, 250);
            });
            self.$('div.post_spam').empty().append(renderToElement('website_forum.spam_search_name', {
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
        var values = Array.from($inputs).map((o) => parseInt(o.value));
        return this.orm.call("forum.post", "mark_as_offensive_batch", [
            this.spamIDs,
            key,
            values,
        ]).then(function () {
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
