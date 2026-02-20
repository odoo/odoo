import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * This interaction is only used by the module website_partnership.
 * The corresponding buttons can be seen at "/partners". We probably want to
 * remove them at some point.
 */
export class PublishManagement extends Interaction {
    static selector = ".js_publish_management";
    dynamicContent = {
        _root: {
            "t-att-class": () => ({
                css_published: this.isPublished,
                css_unpublished: !this.isPublished,
            }),
        },
        ".js_publish_btn": { "t-on-click.prevent": this.onPublishBtnClick },
    };

    setup() {
        this.isPublished = this.el.classList.contains("css_published");
    }

    async onPublishBtnClick() {
        this.isPublished = await this.services.orm.call(
            this.el.dataset.object,
            "website_publish_button",
            [[parseInt(this.el.dataset.id)]]
        );
        const itemEl = this.el.closest("[data-publish]");
        if (itemEl) {
            itemEl.dataset.publish = this.isPublished ? "on" : "off";
        }
    }
}

registry.category("public.interactions").add("website.publish_management", PublishManagement);
