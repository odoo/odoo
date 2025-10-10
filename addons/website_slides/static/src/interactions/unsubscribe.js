import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { SlideUnsubscribeDialog } from "@website_slides/js/public/components/slide_unsubscribe_dialog/slide_unsubscribe_dialog";

export class Unsubscribe extends Interaction {
    static selector = ".o_wslides_js_channel_unsubscribe";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": () => {
                const data = this.el.dataset;
                this.services.dialog.add(SlideUnsubscribeDialog, {
                    channelId: Number(data.channelId),
                    isFollower: !!data.isFollower,
                    enroll: data.enroll,
                    visibility: data.visibility,
                });
            },
        },
    };
}

registry.category("public.interactions").add("website_slides.unsubscribe", Unsubscribe);
