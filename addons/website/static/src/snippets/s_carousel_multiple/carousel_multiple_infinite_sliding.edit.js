import { registry } from "@web/core/registry";
import { getCarouselCenteringIndex } from "@website/utils/misc";
import { CarouselMultipleEdit } from "./carousel_multiple.edit";
import { CarouselMultipleInfiniteSliding } from "./carousel_multiple_infinite_sliding";

const CarouselMultipleInfiniteSlidingEdit = (I) =>
    class extends CarouselMultipleEdit(I) {
        setup() {
            super.setup();
            this.websiteEditService = this.services.website_edit;
            this.isSliding = false;
            this.observer = new MutationObserver(() => {
                // if there are any mutations, create new clones
                this.disconnectSourceObserver();
                this.removeClonedItems();
                this.originalItemsCount =
                    this.innerCarouselEl.querySelectorAll(".carousel-item").length;
                this.cloneCarouselItems();
                this.connectSourceObserver();
            });
            this.connectSourceObserver();
        }

        connectSourceObserver() {
            // track removal/addition of the carousel items
            this.observer.observe(this.innerCarouselEl, {
                childList: true,
            });
            // track the editing of the carousel items text nodes
            this.el.querySelectorAll(".carousel-item:not(.carousel-item_copy)").forEach((item) => {
                this.observer.observe(item, {
                    characterData: true,
                    subtree: true,
                });
            });
        }

        disconnectSourceObserver() {
            this.observer.disconnect();
        }

        destroy() {
            this.observer?.disconnect();
            super.destroy();
        }

        async onClick(ev) {
            if (this.isSliding) {
                return;
            }
            let editingItemEl = ev.currentTarget;
            const carouselItemsEls = [...editingItemEl.parentElement.children];
            const activeItemEl = this.innerCarouselEl.querySelector(".carousel-item.active");
            let fromIndex = carouselItemsEls.indexOf(activeItemEl);
            if (editingItemEl.classList.contains("carousel-item_copy")) {
                const currentIndex = carouselItemsEls.indexOf(editingItemEl);
                const newIndex = (currentIndex % this.originalItemsCount) + this.originalItemsCount;
                // we have to adjust the fromIndex as well
                fromIndex -= currentIndex - newIndex;
                editingItemEl = carouselItemsEls[newIndex];
            }
            const toIndex = getCarouselCenteringIndex(editingItemEl);
            activeItemEl.classList.remove("active");
            this.websiteEditService.callShared("builderOverlay", "toggleOverlaysVisibility", false);
            this.isSliding = true;
            await this.slideCarousel(toIndex, fromIndex);
            this.isSliding = false;
            carouselItemsEls[toIndex].classList.add("active");
            this.websiteEditService.callShared("builderOptions", "updateContainers", [
                editingItemEl,
                {
                    forceUpdate: true,
                },
            ]);
        }
    };

registry
    .category("public.interactions.edit")
    .add("website.carousel_multiple_infinite_sliding_edit", {
        Interaction: CarouselMultipleInfiniteSliding,
        mixin: CarouselMultipleInfiniteSlidingEdit,
    });
