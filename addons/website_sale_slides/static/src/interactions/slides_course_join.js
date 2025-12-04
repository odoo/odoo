import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { WebsiteSlidesCourseJoinLink } from "@website_slides/interactions/slides_course_join";

patch(WebsiteSlidesCourseJoinLink.prototype, {
    /**
     * When the user joins the course, if it's set as "on payment" and the user is logged in,
     * we redirect to the shop page for this course.
     *
     * @override
     */
    async onJoinClick() {
        if (this.channel.enroll === "payment" && !session.is_public) {
            await this.waitFor(this.slidesService.beforeJoin());
            this.services.cart.add(
                {
                    // TODO VCR Ensure productTemplateId is always provided to `addToCart`.
                    // Currently, this works because the product configurator check is bypassed
                    // when the `isBuyNow` option is `True`.
                    productTemplateId: false,
                    productId: this.channel.productId,
                },
                {
                    isBuyNow: true,
                }
            );
        } else {
            await this.waitFor(super.onJoinClick());
        }
    },
});
