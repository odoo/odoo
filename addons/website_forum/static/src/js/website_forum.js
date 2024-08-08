/** @odoo-module **/

import { markup } from "@odoo/owl";
import { FlagMarkAsOffensiveDialog } from "../components/flag_mark_as_offensive/flag_mark_as_offensive";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { cookie } from "@web/core/browser/cookie";;
import { loadWysiwygFromTextarea } from "@web_editor/js/frontend/loadWysiwygFromTextarea";
import publicWidget from "@web/legacy/js/public/public_widget";
import { session } from "@web/session";
import { rpc } from "@web/core/network/rpc";
import { get } from "@web/core/network/http_service";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { scrollTo, closestScrollableY } from "@web/core/utils/scrolling";
import { attachComponent } from "@web/legacy/utils";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { getAdjacentNextSiblings } from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { slideUp } from "@web/core/utils/slide";

publicWidget.registry.websiteForum = publicWidget.Widget.extend({
    selector: '.website_forum',
    events: {
        'click .karma_required': '_onKarmaRequiredClick',
        "click .o_js_forum_tag_follow": "_onTagFollowClick",
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
        this.orm = this.bindService("orm");
        this.http = this.bindService("http");
        this.notification = this.bindService("notification");
    },

    /**
     * @override
     */
    async start() {
        var self = this;
        const _super = this._super.bind(this);

        this.lastsearch = [];
        this.choice = [];

        // float-start class messes up the post layout OPW 769721
        document
            .querySelector('span[data-oe-model="forum.post"][data-oe-field="content"]')
            ?.querySelector("img.float-start")
            ?.classList.remove("float-start");

        // welcome message action button
        var forumLogin = `${window.location.origin}/web?redirect=${encodeURIComponent(window.location.href)}`
        this.el.querySelector(".forum_register_url")?.setAttribute("href", forumLogin);

        // Initialize forum's tooltips
        this.el.querySelectorAll("[data-bs-toggle='tooltip']")?.forEach((tooltipEl) => {
            Tooltip.getOrCreateInstance(tooltipEl, {
                delay: 0,
            });
        });
        this.el.querySelectorAll("[data-bs-toggle='popover']")?.forEach((popoverEl) => {
            Popover.getOrCreateInstance(popoverEl, {
                offset: '10',
            });
        });

        const element = document.querySelector("input.js_select_menu");
        if (element) {
            // Take default tags from the input value
            const defaultChoices = [];
            JSON.parse(element.getAttribute("data-init-value"))?.forEach((x) => {
                defaultChoices.push({ id: x.id, label: x.name, value: x.id, isNew: false });
            });
            let defaulValue = defaultChoices.map((choice) => choice.id);
            defaulValue = defaulValue.join(",");

            const tagsSelectMenu = await attachComponent(this, element.parentNode, SelectMenu, {
                searchPlaceholder: _t("Please enter 2 or more characters"),
                placeholder: _t("Tags"),
                element: element,
                multiSelect: true,
                choices: defaultChoices || [],
                onSelect: (value) => {
                    tagsSelectMenu?.update({
                        value: value,
                    });
                },
                choiceFetchFunction: (searchString) => {
                    const forumID = $("#wrapwrap").data("forum_id");
                    return new Promise((resolve, reject) => {
                        get(
                            `/forum/get_tags?query=${searchString}&limit=${50}&forum_id=${forumID}`
                        ).then((result) => {
                            result.forEach((choice) => {
                                choice.value = choice.name;
                                choice.label = choice.name;
                            });
                            result = this.choice.length ? result.concat(this.choice) : result;
                            resolve(result);
                        });
                    });
                },
                onCreate: (choice) => {
                    const karma = document.querySelector("#karma").value;
                    const editKarma = document.querySelector("#karma_edit_retag").value;
                    if(parseInt(karma) >= parseInt(editKarma)) {
                        return choice || [];
                    }
                    return false;
                },
                value: defaulValue || "",
            });
        }

        document.querySelectorAll("textarea.o_wysiwyg_loader").forEach((textarea) => {
            const editorKarma = textarea.dataset.karma || 0; // default value for backward compatibility
            const form = textarea.closest("form");
            const hasFullEdit = parseInt(document.querySelector("#karma").value) >= editorKarma;

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
            loadWysiwygFromTextarea(self, textarea, options).then((wysiwyg) => {
                // float-start class messes up the post layout OPW 769721
                form.querySelector(".note-editable")
                    .querySelectorAll("img.float-start")
                    .forEach((img) => img.classList.remove("float-start"));
            });
        });

        this.el.querySelectorAll(".o_wforum_bio_popover").forEach((authorBox) => {
            Popover.getOrCreateInstance(authorBox, {
                trigger: 'hover',
                offset: '10',
                animation: false,
                html: true,
                customClass: 'o_wforum_bio_popover_container shadow-sm',
            });
        });

        const replyEl = this.el.querySelector("#post_reply");
        replyEl?.addEventListener("shown.bs.collapse", function (e) {
            const scrollingElement = closestScrollableY(replyEl.parentNode);
            scrollTo(replyEl, {
                behavior: "smooth",
                offset: scrollingElement.clientHeight - replyEl.clientHeight,
            });
        });
        document.querySelectorAll('.o_wforum_question, .o_wforum_answer, .o_wforum_post_comment, .o_wforum_last_activity')
            .forEach((post) => {
                post.querySelector('.o_wforum_relative_datetime').textContent = luxon.DateTime
                    .fromSQL(post.dataset.lastActivity, {zone: 'utc'})
                    .toRelative();
            });
        return _super.apply(...arguments);
    },

    /**
     * Check if the user is public, if it's true send a warning alert saying the action cannot be performed.
     **/
    _warnIfPublicUser: function() {
        if (session.is_website_user) {
            this._displayAccessDeniedNotification(
                markup(_t('Oh no! Please <a href="%s">sign in</a> to perform this action', "/web/login"))
            );
            return true;
        }
        return false;
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

        const form = ev.currentTarget;
        const title = form.querySelector("input[name=post_name]");
        const textarea = form.querySelector("textarea[name=content]");
        // It's not really in the textarea that the user write at first
        const fillableTextAreaEl = form.querySelector(".o_wysiwyg_textarea_wrapper");
        const isTextAreaFilled = fillableTextAreaEl &&
            (fillableTextAreaEl.innerText.trim() || fillableTextAreaEl.querySelector("img"));

        if (title && title.required) {
            if (title.value) {
                title.classList.remove("is-invalid");
            } else {
                title.classList.add("is-invalid");
                validForm = false;
            }
        }

        // Because the textarea is hidden, we add the red or green border to its container
        if (textarea && textarea.required) {
            const textareaContainer = form.querySelector(".o_wysiwyg_textarea_wrapper");
            if (!isTextAreaFilled) {
                textareaContainer.classList.add("border", "border-danger", "rounded-top");
                validForm = false;
            } else {
                textareaContainer.classList.remove("border", "border-danger", "rounded-top");
            }
        }

        if (validForm) {
            // Stores social share data to display modal on next page.
            if (form.querySelector(".oe_social_share_call")) {
                sessionStorage.setItem('social_share', JSON.stringify({
                    targetType: ev.currentTarget.querySelector(".o_wforum_submit_post").dataset.socialTargetType,
                }));
            }
        } else {
            ev.preventDefault();
            setTimeout(function() {
                const buttons = Array.from(
                    form.querySelectorAll('button[type="submit"], a.a-submit')
                );
                buttons.forEach((btn) => {
                    const icon = btn.querySelector("i");
                    if (icon) {
                        icon.remove();
                    }
                    btn.removeAttribute("disabled");
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
        if (this._warnIfPublicUser()) {
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
    _onTagFollowClick: function (ev) {
        const closestBtn = ev.target.closest("button");
        if (closestBtn) {
            ev.currentTarget.querySelector(".o_js_forum_tag_link").classList.toggle("text-muted");
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onUserInfoMouseEnter: function (ev) {
        const bioExpand = ev.currentTarget.parentNode.querySelector(".o_forum_user_bio_expand");
        setTimeout(() => {
            bioExpand.style.display = "block";
        }, 500);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onUserInfoMouseLeave: function (ev) {
        const bioExpand = ev.currentTarget.parentNode.querySelector(".o_forum_user_bio_expand");
        // stop animation which are in queue
        bioExpand.style.transition = "none";
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onUserBioExpandMouseLeave: function (ev) {
        /**
         * This is starting a new animation that gradually changes the
         * selected element's opacity to 0 over a short period of time (200ms),
         * giving the effect of fading out. After the animation is complete,
         * the element's display style property is set to 'none'.
         */
        const element = ev.currentTarget;
        element.style.transition = "opacity 0.2s ease-out";
        element.style.opacity = "0";
        setTimeout(() => {
            element.style.display = "none";
        }, 200);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onFlagAlertClick: function (ev) {
        ev.preventDefault();
        if (this._warnIfPublicUser()) {
            return;
        }
        const elem = ev.currentTarget;
        rpc(
            elem.dataset.href || (elem.getAttribute('href') !== '#' && elem.getAttribute('href')) || elem.closest('form').getAttribute('action'),
        ).then(data => {
            if (data.error) {
                const message = data.error === 'post_already_flagged'
                    ? _t("This post is already flagged")
                    : data.error === 'post_non_flaggable'
                        ? _t("This post can not be flagged")
                        : data.error;
                this._displayAccessDeniedNotification(message);
            } else if (data.success) {
                const child = elem.firstElementChild;
                if (data.success === 'post_flagged_moderator') {
                    const countFlaggedPosts = this.el.querySelectorAll('#count_posts_queue_flagged');
                    elem.innerText = _t(' Flagged');
                    elem.prepend(child);
                    if (countFlaggedPosts) {
                        countFlaggedPosts.forEach((flaggedPostEl) => {
                            flaggedPostEl.classList.remove('d-none', 'bg-light');
                            flaggedPostEl.classList.add('bg-danger');
                            flaggedPostEl.innerText = parseInt(flaggedPostEl.innerText, 10) + 1;
                        });
                    }
                    getAdjacentNextSiblings(elem)
                        .filter((sibling) => sibling.classList?.contains("flag_validator"))
                        .forEach((sibling) => {
                            sibling.classList.remove("d-none");
                        });
                } else if (data.success === 'post_flagged_non_moderator') {
                    const forumAnswer = elem.closest('.o_wforum_answer');
                    elem.innerText = _t(' Flagged');
                    elem.prepend(child);
                    slideUp(forumAnswer, 1000, () => {
                        forumAnswer.style.display = "none";
                    });
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
        if (this._warnIfPublicUser()) {
            return;
        }
        const btn = ev.currentTarget;
        const href = btn.getAttribute("data-href");
        rpc(href).then((data) => {
            if (data.error) {
                const message = data.error === 'own_post' ? _t('Sorry, you cannot vote for your own posts') : data.error;
                this._displayAccessDeniedNotification(message);
            } else {
                const container = btn.closest(".vote");
                const items = Array.from(container.children);
                const voteUp = items.find((item) => item.classList.contains("vote_up"));
                const voteDown = items.find((item) => item.classList.contains("vote_down"));
                const voteCount = items.find((item) => item.classList.contains("vote_count"));
                const userVote = parseInt(data["user_vote"]);

                if (userVote === 1) {
                    voteUp.setAttribute("disabled", true);
                    voteDown.setAttribute("disabled", false);
                }

                items.forEach((item) =>
                    item.classList.remove(
                        "text-success",
                        "text-danger",
                        "text-muted",
                        "opacity-75",
                        "o_forum_vote_animate"
                    )
                );
                void container.offsetWidth; // Force a refresh

                if (userVote === 1) {
                    voteUp.classList.add("text-success");
                    voteCount.classList.add("text-success");
                    voteDown.classList.remove("karma_required");
                }
                if (userVote === -1) {
                    voteDown.classList.add("text-danger");
                    voteCount.classList.add("text-danger");
                    voteUp.classList.remove("karma_required");
                }
                if (userVote === 0) {
                    voteCount.classList.add("text-muted", "opacity-75");
                    if (!voteDown.getAttribute("data-can-downvote")) {
                        voteDown.classList.add("karma_required");
                    }
                    if (!voteUp.getAttribute("data-can-upvote")) {
                        voteUp.classList.add("karma_required");
                    }
                }
                voteCount.innerHTML = data["vote_count"];
                voteCount.classList.add("o_forum_vote_animate");
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
        if (this._warnIfPublicUser()) {
            return;
        }
        const link = ev.currentTarget;
        const target = link.dataset.target;
        const data = await rpc(link.dataset.href);
        if (data.error) {
            const message = data.error === 'own_post' ? _t('Sorry, you cannot select your own posts as best answer') : data.error;
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
        if (this._warnIfPublicUser()) {
            return;
        }
        this.call("dialog", "add", ConfirmationDialog, {
            body: _t("Are you sure you want to delete this comment?"),
            confirmLabel: _t("Delete"),
            confirm: () => {
                const deleteBtn = ev.currentTarget;
                rpc(deleteBtn.closest("form").attributes.action.value).then(() => {
                    deleteBtn.closest(".o_wforum_post_comment").remove();
                }).catch((error) => {
                    this.notification.add(error.data.message, {
                        title: _t("Karma Error"),
                        sticky: false,
                        type: 'warning',
                    });
                });
            },
            cancel: () => {},
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onCloseIntroClick: function (ev) {
        ev.preventDefault();
        cookie.set('forum_welcome_message', false, 24 * 60 * 60 * 365, 'optional');
        const forumIntro = document.querySelector(".forum_intro");
        slideUp(forumIntro, 200, () => {
            forumIntro.style.display = "none";
        })
        return true;
    },
    /**
     * @private
     * @param {Event} ev
     */
    async _onFlagValidatorClick(ev) {
        ev.preventDefault();
        const currentTarget = ev.currentTarget;
        await rpc(ev.currentTarget.dataset.action);
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
        this.spamIDs = JSON.parse(this.el.querySelector(".modal").dataset.spamIds);
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
        const spamInput = this.el.querySelector(".modal .tab-pane.active input");
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
                const parsed = parser.parseFromString(r.content, "text/html");
                r.content = parsed.body.textContent.substring(0, 250);
            });
            const postSpamDivs = document.querySelectorAll("div.post_spam");
            postSpamDivs.forEach((div) => {
                div.replaceChildren();
                div.appendChild(
                    renderToElement("website_forum.spam_search_name", { posts: o })
                );
            });
        });
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onMarkSpamClick: function (ev) {
        const key = this.el.querySelector(".modal .tab-pane.active").dataset.key;
        const inputs = this.el.querySelectorAll(
            ".modal .tab-pane.active input.form-check-input:checked"
        );
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
