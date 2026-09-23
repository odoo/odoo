import { registry } from "@web/core/registry";
import { AnnouncementScroll } from "./announcement_scroll";
import { patchDynamicContentEntry } from "@web/public/utils";
import { closestElement } from "@html_editor/utils/dom_traversal";

export const AnnouncementScrollEdit = (I) =>
    class extends I {
        setup() {
            // add the shift caused by edition
            patchDynamicContentEntry(
                this.dynamicContent,
                ".s_announcement_scroll_marquee_container",
                "t-att-style",
                () => ({
                    // `--marquee-item-size` is set by `updateMarqueeLayout`,
                    // the other vars are set by the plugin on selection change
                    transform: `translateX(${this.parallaxPosition}%) translateX(calc((var(--marquee-item-selected-index, 0) * (var(--marquee-intial-item-size, var(--marquee-item-size)) - var(--marquee-item-size)) + var(--marquee-intial-offset, 0)) * 1px))`,
                })
            );
            super.setup();
            this.websiteEditService = this.services.website_edit;
            this.partialCleanUp = true;
            this.resizeObserver = new ResizeObserver(() => {
                this.protectSyncAfterAsync(() => {
                    this.updateMarqueeLayout();
                })();
            });
        }
        start() {
            super.start();
            this.resizeObserver.observe(this.marqueeItemEl);
            this.resizeObserver.observe(this.el);
        }
        destroy() {
            this.resizeObserver.disconnect();
            this.partialCleanUp = false;
            super.destroy();
        }
        undoMarqueeLayout() {
            if (this.partialCleanUp) {
                const marqueeItemElWidth = this.marqueeItemEl.offsetWidth;
                const itemsPerContainer = Math.ceil(
                    this.marqueeContainerEl.parentElement.offsetWidth / marqueeItemElWidth
                );
                const excessCount =
                    this.marqueeContainerEl.childElementCount - (itemsPerContainer * 2 + 2);
                const anchorNode = document.getSelection().anchorNode;
                const itemWithSelection =
                    anchorNode && closestElement(anchorNode, ".s_announcement_scroll_marquee_item");
                for (let i = 0; i < excessCount; i++) {
                    if (this.marqueeContainerEl.lastElementChild === itemWithSelection) {
                        break;
                    }
                    this.marqueeContainerEl.lastElementChild.remove();
                }
            } else {
                super.undoMarqueeLayout();
            }
        }
        updateMarqueeLayout() {
            super.updateMarqueeLayout();
            const itemAnimation = this.marqueeItemEl.getAnimations();
            for (const cloneEl of this.marqueeContainerEl.children) {
                if (cloneEl !== this.marqueeItemEl) {
                    cloneEl.getAnimations().forEach((animation, index) => {
                        animation.currentTime = itemAnimation[index].currentTime;
                    });
                }
                this.websiteEditService.callShared("domReferenceMap", "register", cloneEl);
            }
        }
    };

registry.category("public.interactions.edit").add("website.announcement_scroll", {
    Interaction: AnnouncementScroll,
    mixin: AnnouncementScrollEdit,
});
