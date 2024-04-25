/** @odoo-module **/

import { markup } from "@odoo/owl";
import { FlagMarkAsOffensiveDialog } from "../components/flag_mark_as_offensive/flag_mark_as_offensive";
import dom from "@web/legacy/js/core/dom";
import { cookie } from "@web/core/browser/cookie";;
import { loadWysiwygFromTextarea } from "@web_editor/js/frontend/loadWysiwygFromTextarea";
import publicWidget from "@web/legacy/js/public/public_widget";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
import { escape } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { getAdjacentNextSiblings } from "@web_editor/js/editor/odoo-editor/src/utils/utils";

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
        'click .comment_delete': '_onDeleteCommentClick',
        'click .js_close_intro': '_onCloseIntroClick',
        'click .answer_collapse': '_onExpandAnswerClick',
        'submit .js_wforum_submit_form:has(:not(.karma_required).o_wforum_submit_post)': '_onSubmitForm',
    },

    init() {
        this._super(...arguments);
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
        document.querySelector('span[data-oe-model="forum.post"][data-oe-field="content"]')
            .querySelector('img.float-start')
            .classList.remove('float-start');

        // welcome message action button
        var forumLogin = `${window.location.origin}/web?redirect=${encodeURIComponent(window.location.href)}`
        document.querySelector('.forum_register_url').setAttribute('href', forumLogin);

        // Initialize forum's tooltips
        const tooltip = new Tooltip(this.el.querySelector('[data-bs-toggle="tooltip"]'), { delay : 0});
        const popover = new Popover(this.el.querySelector('[data-bs-toggle="popover"]'), { offset : 8 });
        
        // TODO-shsa : select2 is a jquery plugin, we should use owl select2 instead

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

        document.querySelectorAll('textarea.o_wysiwyg_loader').forEach((textarea) => {
            var editorKarma = textarea.dataset.karma || 0; // default value for backward compatibility
            var form = textarea.closest('form');
            var hasFullEdit = parseInt(document.querySelector("#karma").value) >= editorKarma;

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
                    // Id is retrieved from URL, which is either:
                    // - /forum/name-1/post/something-5
                    // - /forum/name-1/post/something-5/edit
                    // TODO: Make this more robust.
                    res_id: +window.location.pathname.split('-').slice(-1)[0].split('/')[0],
                },
                resizable: true,
                userGeneratedContent: true,
                height: 350,
            };
            options.allowCommandLink = hasFullEdit;
            options.allowCommandImage = hasFullEdit;
            loadWysiwygFromTextarea(self, textarea, options).then(wysiwyg => {
                // float-start class messes up the post layout OPW 769721
                form.querySelector('.note-editable').querySelectorAll('img.float-start').forEach(img => img.classList.remove('float-start'));
            });
        });

        document.querySelectorAll('.o_wforum_bio_popover').forEach((authorBox) => {
            new Popover(authorBox, {
                trigger: 'hover',
                offset: '10',
                animation: false,
                html: true,
                customClass: 'o_wforum_bio_popover_container shadow-sm',
            });
        });

        document.querySelector('#post_reply').addEventListener('shown.bs.collapse', function (e) {
            const replyEl = document.querySelector('#post_reply');
            const scrollingElement = replyEl.parentNode.closestScrollable();
            dom.scrollTo(replyEl, {
                forcedOffset: scrollingElement.clientHeight - replyEl.clientHeight,
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

        let form = ev.currentTarget;
        let title = form.querySelector('input[name=post_name]');
        let textarea = form.querySelector('textarea[name=content]');
        // It's not really in the textarea that the user write at first
        const fillableTextAreaEl = form.querySelector(".o_wysiwyg_textarea_wrapper");
        const isTextAreaFilled = fillableTextAreaEl &&
            (fillableTextAreaEl.innerText.trim() || fillableTextAreaEl.querySelector("img"));

        if (title && title.required) {
            if (title.value) {
                title.classList.remove('is-invalid');
            } else {
                title.classList.add('is-invalid');
                validForm = false;
            }
        }

        // Because the textarea is hidden, we add the red or green border to its container
        if (textarea && textarea.required) {
            let textareaContainer = form.querySelector('.o_wysiwyg_textarea_wrapper');
            if (!isTextAreaFilled) {
                textareaContainer.classList.add('border', 'border-danger', 'rounded-top');
                validForm = false;
            } else {
                textareaContainer.classList.remove('border', 'border-danger', 'rounded-top');
            }
        }

        if (validForm) {
            // Stores social share data to display modal on next page.
            if (form.querySelector('.oe_social_share_call')) {
                sessionStorage.setItem('social_share', JSON.stringify({
                    targetType: ev.currentTarget.querySelector('.o_wforum_submit_post').dataset.socialTargetType,
                }));
            }
        } else {
            ev.preventDefault();
            setTimeout(function() {
                let buttons = Array.from(form.querySelectorAll('button[type="submit"], a.a-submit'));
                buttons.forEach((btn) => {
                    let icon = btn.querySelector('i');
                    if (icon) {
                        icon.remove();
                    }
                    btn.disabled = false;
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
        let followBox = ev.currentTarget.querySelector('.o_forum_tag_follow_box');
        followBox.style.display = 'block';
    },
    /**
     * @private
     * @param {Event} ev
     */
    // TODO-shsa : check .stop()
    /**
     * $(ev.currentTarget): This is selecting the HTML element that triggered the current event.
     * For example, if this code is running in response to a button click, ev.currentTarget would be the button that was clicked.

    .find('.o_forum_tag_follow_box'):
    This is searching within the selected element for any child elements
    that have the class o_forum_tag_follow_box.

    .stop(): This is stopping any animations that are currently running on the selected elements.

    .fadeOut(): This is starting a new animation that gradually changes the selected elements'
    opacity to 0, giving the effect of fading out.

    .css('display', 'none'): After the fade out animation,
    this is setting the CSS display property of the selected elements to none,
    effectively hiding them from the layout of the page.
    */
    _onTagFollowBoxMouseLeave: function (ev) {
        let followBox = ev.currentTarget.querySelector('.o_forum_tag_follow_box');
        // The stop() function in jQuery is used to stop an animation or effect before it is finished.
        // The stop() function is not directly available in vanilla JavaScript.
        // However, you can achieve a similar effect by using clearInterval()
        // to stop a running interval that's controlling an animation.
        if (followBox.fadeEffect) {
            clearInterval(followBox.fadeEffect);
        }
        followBox.style.opacity = '1';
        followBox.fadeEffect = setInterval(function () {
            if (!followBox.style.opacity) {
                followBox.style.opacity = '1';
            }
            if (followBox.style.opacity > '0') {
                followBox.style.opacity -= '0.1';
            } else {
                clearInterval(followBox.fadeEffect);
                followBox.style.display = 'none';
            }
        }, 20);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onUserInfoMouseEnter: function (ev) {
        let bioExpand = ev.currentTarget.parentNode.querySelector('.o_forum_user_bio_expand');
        setTimeout(function() {
            bioExpand.style.display = 'block';
        }, 500);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onUserInfoMouseLeave: function (ev) {
        let bioExpand = ev.currentTarget.parentNode.querySelector('.o_forum_user_bio_expand');
        // clearQueue() has no direct equivalent in vanilla JS,
        // but if you're using it to stop animations, you can do so by removing the transition property
        bioExpand.style.transition = 'none';
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onUserBioExpandMouseLeave: function (ev) {
        /**
         * .fadeOut('fast'): This is starting a new animation that gradually
         * changes the selected element's opacity to 0 over a short period of time (200ms),
         * giving the effect of fading out. After the animation is complete,
         * the element's display style property is set to 'none'.
        */
        let element = ev.currentTarget;
        element.style.transition = 'opacity 0.2s ease-out';
        element.style.opacity = '0';
        setTimeout(function() {
            element.style.display = 'none';
        }, 200);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onFlagAlertClick: function (ev) {
        ev.preventDefault();
        const elem = ev.currentTarget;
        rpc(
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
                    getAdjacentNextSiblings(elem).forEach((sibling) => {
                        if (sibling.classList.contains('flag_validator')) {
                            sibling.classList.remove('d-none');
                        }
                    });
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
        const btn = ev.currentTarget;
        let href = btn.getAttribute('data-href');
        rpc(href).then(data => {
            if (data.error) {
                const message = data.error === 'own_post'
                    ? 'Sorry, you cannot vote for your own posts'
                    : data.error === 'anonymous_user'
                        ? `<p>Oh no! Please <a href="%s">sign in</a> to vote</p>`.replace('%s', "/web/login")
                        : data.error;
                this._displayAccessDeniedNotification(message);
            } else {
                const container = btn.closest('.vote');
                const items = Array.from(container.children);
                let voteUp = items.find(item => item.classList.contains('vote_up'));
                let voteDown = items.find(item => item.classList.contains('vote_down'));
                let voteCount = items.find(item => item.classList.contains('vote_count'));
                const userVote = parseInt(data['user_vote']);

                voteUp.disabled = userVote === 1;
                voteDown.disabled = userVote === -1;

                items.forEach(item => item.classList.remove('text-success', 'text-danger', 'text-muted', 'opacity-75', 'o_forum_vote_animate'));
                container.offsetWidth; // Force a refresh

                if (userVote === 1) {
                    voteUp.classList.add('text-success');
                    voteCount.classList.add('text-success');
                    voteDown.classList.remove('karma_required');
                }
                if (userVote === -1) {
                    voteDown.classList.add('text-danger');
                    voteCount.classList.add('text-danger');
                    voteUp.classList.remove('karma_required');
                }
                if (userVote === 0) {
                    voteCount.classList.add('text-muted', 'opacity-75');
                    if (!voteDown.getAttribute('data-can-downvote')) {
                        voteDown.classList.add('karma_required');
                    }
                    if (!voteUp.getAttribute('data-can-upvote')) {
                        voteUp.classList.add('karma_required');
                    }
                }
                voteCount.innerHTML = data['vote_count'];
                voteCount.classList.add('o_forum_vote_animate');
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
        const data = await rpc(link.dataset.href);
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
        const data = await rpc(link.dataset.href);
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
        const link = ev.currentTarget;
        const container = link.closest('.o_wforum_post_comments_container');

        rpc(link.closest('form').action).then(function () {
            const comment = link.closest('.o_wforum_post_comment');
            comment.parentNode.removeChild(comment);

            const comments = container.querySelectorAll('.o_wforum_post_comment');
            const count = comments.length;
            if (count) {
                const commentCount = container.querySelector('.o_wforum_comments_count');
                commentCount.textContent = count;
            } else {
                const commentCountHeader = container.querySelector('.o_wforum_comments_count_header');
                if (commentCountHeader) {
                    commentCountHeader.parentNode.removeChild(commentCountHeader);
                }
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
        /*
            The slideUp() method in jQuery hides the matched elements with a sliding motion.
            It adjusts the height of the element over time,
            creating a slide up effect, until the element's height is 0,
            at which point the element is hidden.
        */
        const forumIntro = document.querySelector('.forum_intro');
        forumIntro.style.transition = 'height 0.6s ease-out';
        forumIntro.style.height = '0';
        setTimeout(function() {
            forumIntro.style.display = 'none';
        }, 600);
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
        const template = await rpc(ev.currentTarget.dataset.action);
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
        this.spamIDs = this.document.querySelector('.modal').dataset.spam-ids;
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
        var spamInput = this.document.querySelector('.modal .tab-pane.active input');
        spamInput.checked = true;
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onSpamSearchInput: function (ev) {
        const self = this;
        const toSearch = ev.currentTarget.value;
        return this.orm.searchRead(
            "forum.post",
            [['id', 'in', self.spamIDs],
                '|',
                ['name', 'ilike', toSearch],
                ['content', 'ilike', toSearch]],
            ['name', 'content']
        ).then(function (o) {
            Object.values(o).forEach((r) => {
                const parser = new DOMParser();
                const parsed = parser.parseFromString(r.content, 'text/html');
                r.content = parsed.body.textContent.substring(0, 250);
            });
            const postSpamDivs = document.querySelectorAll('div.post_spam');
            postSpamDivs.forEach((div) => {
                while (div.firstChild) {
                    div.removeChild(div.firstChild);
                }
                div.appendChild(renderToElement('website_forum.spam_search_name', { posts: o }));
            });
        });
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onMarkSpamClick: function (ev) {
        const key = document.querySelector('.modal .tab-pane.active').dataset.key;
        const inputs = document.querySelectorAll('.modal .tab-pane.active input.form-check-input:checked');
        const values = Array.from(inputs).map((o) => parseInt(o.value));
        return this.orm.call("forum.post", "mark_as_offensive_batch", [
            this.spamIDs,
            key,
            values,
        ]).then(function () {
            window.location.reload();
        });
    },
});
