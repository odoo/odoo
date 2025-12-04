import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { redirect } from "@web/core/utils/urls";
import { SlidesCourseJoinPopup } from "@website_slides/js/public/components/course_join_popup/course_join_popup";
import { session } from "@web/session";

export class WebsiteSlidesCourseJoinLink extends Interaction {
    static selector = ".o_wslides_js_course_join_link";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": this.onJoinClick,
        },
    };

    setup() {
        this.slidesService = this.services.website_slides;
        this.popover = this.services.popover;
        const data = this.el.dataset;
        this.slidesService.setChannel({
            id: Number(data.channelId),
            enroll: data.channelEnroll,
            inviteHash: data.inviteHash,
            invitePartnerId: Number(data.invitePartnerId),
            invitePreview: !!data.invitePreview,
            isMemberOrInvited: !!data.isMemberOrInvited,
        });
        this.joinAfterQuiz = data.joinAfterQuiz;
        this.channel = this.slidesService.data.channel;
    }

    /**
     * @param {MouseEvent} event
     */
    async onJoinClick() {
        if (
            this.channel.invitePreview ||
            (this.channel.enroll === "invite" && this.channel.isMemberOrInvited)
        ) {
            return this.joinChannel(this.channel.id);
        }

        if (this.channel.enroll !== "invite") {
            if (session.is_public && this.joinAfterQuiz) {
                await this.waitFor(this.slidesService.beforeJoin());
                this.redirectToLogin();
            } else if (!this.channel.isMember) {
                return this.joinChannel(this.channel.id);
            }
        }
    }

    /**
     * Builds a login page that then redirects to this slide page, or the channel if the course
     * is not configured as public enroll type.
     */
    redirectToLogin() {
        const url = new URL(window.location.pathname, window.location.origin);
        if (this.channel.enroll === "public") {
            if (document.location.href.indexOf("fullscreen") !== -1) {
                url.searchParams.append("fullscreen", 1);
            }
        } else {
            url.pathname = `/slides/${encodeURIComponent(this.channel.id)}`;
        }
        const redirectURL = new URL("/web/login", window.location.origin);
        redirectURL.searchParams.append("redirect", url.href);
        redirect(redirectURL.href);
    }

    /**
     * @param {integer} channelId
     */
    async joinChannel(channelId) {
        const data = await this.waitFor(this.slidesService.joinChannel(channelId));
        if (data.error) {
            if (data.error === "public_user") {
                this.popover.add(this.el, SlidesCourseJoinPopup, {
                    channelId: channelId,
                    courseUrl: encodeURIComponent(document.URL),
                    errorSignupAllowed: data.error_signup_allowed,
                    invitePreview: this.channel.invitePreview,
                    inviteHash: this.channel.inviteHash,
                    invitePartnerId: this.channel.invitePartnerId,
                    isPartnerWithoutUser: !!this.el.dataset.isPartnerWithoutUser,
                });
            } else if (data.error === "join_done") {
                this.popover.add(this.el, SlidesCourseJoinPopup, {
                    text: _t("You have already joined this channel"),
                });
            } else {
                this.popover.add(this.el, SlidesCourseJoinPopup, {
                    text: _t("Unknown error"),
                });
            }
        }
    }
}

registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesCourseJoinLink", WebsiteSlidesCourseJoinLink);
