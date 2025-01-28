import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class SlideArchive extends Interaction {
    static selector = ".o_wslides_js_slide_archive";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": this.openDialog,
        },
    };

    openDialog() {
        const slideId = this.el.dataset.slideId;
        this.services.dialog.add(ConfirmationDialog, {
            title: _t("Archive Content"),
            body: _t("Are you sure you want to archive this content?"),
            confirmLabel: _t("Archive"),
            confirm: async () => {
                /**
                 * Calls 'archive' on slide controller and then visually removes the slide dom element
                 */
                const isArchived = await this.waitFor(rpc("/slides/slide/archive", { slide_id: slideId, }));
                if (isArchived) {
                    this.el.closest(".o_wslides_slides_list_slide")?.remove();
                    const categories = document.querySelectorAll(".o_wslides_slide_list_category");
                    for (const category in categories) {
                        const categoryHeaderEl = category.querySelector(".o_wslides_slide_list_category_header");
                        const categorySlideCountEl = category.querySelector(".o_wslides_slides_list_slide:not(.o_not_editable)").length;
                        const emptyFlagContainerEl = categoryHeaderEl.querySelector(".o_wslides_slides_list_drag");
                        const emptyFlag = emptyFlagContainerEl.querySelector("small").length === 0;
                        if (categorySlideCountEl === 0 && emptyFlag) {
                            const smallEl = document.createElement("small");
                            smallEl.classList.add("ms-1 text-muted fw-bold");
                            smallEl.innerText = _t("(empty)");
                            this.insert(smallEl, emptyFlagContainerEl);
                        }
                    }
                }
            },
            cancel: () => { },
        });
    }
}

registry
    .category("public.interactions")
    .add("website_slides.slide_archive", SlideArchive);
