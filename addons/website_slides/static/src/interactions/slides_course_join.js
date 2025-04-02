import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { redirect } from "@web/core/utils/urls";
import { getDataFromEl } from "@web/public/utils";

class WebsiteSlidesCourseJoinLink extends Interaction {
    static selector = ".o_wslides_js_course_join_link";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": this.onJoinClick,
        },
    };

    setup() {
        const quizService = this.services.slides_course_quiz;
        this.courseJoinService = this.services.slides_course_join;
        this.data = Object.assign(getDataFromEl(this.el), quizService.get());
        console.log("COURSE JOIN DATA:", this.data);
    }

    /**
     * @param {MouseEvent} event
     */
    async onJoinClick(event) {
        console.log("JOIN:", event, this);
        if (
            this.data.invitePreview ||
            (this.data.channelEnroll === "invite" && this.data.isMemberOrInvited)
        ) {
            this.joinChannel(this.data.channelId);
            return;
        }

        if (this.data.channelEnroll !== "invite") {
            if (this.data.publicUser) {
                await this.courseJoinService.beforeJoin();
                this.redirectToLogin();
            } else if (!this.data.isMember) {
                this.joinChannel(this.data.channelId);
            }
        }
    }

    /**
     * Builds a login page that then redirects to this slide page, or the channel if the course
     * is not configured as public enroll type.
     */
    redirectToLogin() {
        const url = new URL(window.location.pathname, window.location.origin);
        if (this.data.channelEnroll === "public") {
            if (document.location.href.indexOf("fullscreen") !== -1) {
                url.searchParams.append("fullscreen", 1);
            }
        } else {
            url.pathname = `/slides/${encodeURIComponent(this.channel.channelId)}`;
        }
        const redirectURL = new URL("/web/login", window.location.origin);
        redirectURL.searchParams.append("redirect", url.href);
        redirect(redirectURL.href);
    }

    /**
     * @param {HTMLElement} el
     * @param {String} message
     */
    // TODO: get rid of jquery
    popoverAlert(el, message) {
        $(el)
            .popover({
                trigger: "focus",
                delay: { hide: 300 },
                placement: "bottom",
                container: "body",
                html: true,
                content: function () {
                    return message;
                },
            })
            .popover("show");
    }

    /**
     * @param {integer} channelId
     */
    // TODO: use events to trigger from outside
    // OR ADD to utils function
    async joinChannel(channelId) {
        const data = await rpc("/slides/channel/join", { channel_id: channelId });
        if (!data.error) {
            await this.courseJoinService.afterJoin();
        } else {
            if (data.error === "public_user") {
                const popupContent = renderToElement("slide.course.join.popupContent", {
                    channelId: channelId,
                    courseUrl: this.data.redirectURL, // TODO: maybe replace with encodeURIComponent(document.URL)
                    errorSignupAllowed: data.error_signup_allowed,
                    invitePreview: this.data.invitePreview,
                    inviteHash: this.data.inviteHash,
                    invitePartnerId: this.data.invitePartnerId,
                    isPartnerWithoutUser: this.data.isPartnerWithoutUser,
                });
                this.popoverAlert(this.el, popupContent);
            } else if (data.error === "join_done") {
                this.popoverAlert(this.el, _t("You have already joined this channel"));
            } else {
                this.popoverAlert(this.el, _t("Unknown error"));
            }
        }
    }
}

registry
    .category("public.interactions")
    .add("website_slides.WebsiteSlidesCourseJoinLink", WebsiteSlidesCourseJoinLink);
