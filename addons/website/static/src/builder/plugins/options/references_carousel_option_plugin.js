import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { END } from "@html_builder/utils/option_sequence";

class ReferencesCarouselOptionPlugin extends Plugin {
    static id = "referencesCarouselOption";

    get resources() {
        return {
            builder_options: [
                withSequence(END, {
                    template: "website.ReferencesCarouselOption",
                    selector: ".s_references_carousel",
                }),
            ],
            on_will_clone_handlers: [this.onWillClone.bind(this)],
            on_cloned_handlers: [this.onCloned.bind(this)],
            on_remove_handlers: [this.onRemove.bind(this)],
            change_current_options_containers_listeners: [this.onSelectionChange.bind(this)],
        };
    }

    // Apply the 'snippet-selected' class to the snippet when it is
    // selected in the editor to style it(pause the animation)
    onSelectionChange(containers) {
        // Find all references carousels in the document
        const allReferencesCarouselEls = this.editable.querySelectorAll('.s_references_carousel');

        // Add or remove the 'snippet-selected' class to all references carousels
        allReferencesCarouselEls.forEach(carouselEl => {
            carouselEl.classList.toggle(
                'snippet-selected',
                containers.some(container => container.element === carouselEl)
            );
        });
    }

    onWillClone({ originalEl }) {
        // If the original element is an img inside a li.item, we need to
        // redirect the clone to target the li.item instead. We'll store this
        // information for the clone operation.
        if (originalEl.matches('.s_references_carousel .s_references_carousel_item img')) {
            const liItemEl = originalEl.closest('.s_references_carousel_item');
            if (liItemEl) {
                // Store the target li element on the original img element for the clone operation
                originalEl._cloneTarget = liItemEl;
            }
        }
    }

    onCloned({ cloneEl, originalEl }) {
        // If we cloned an img element that had a _cloneTarget, we need to handle this specially
        if (originalEl._cloneTarget && cloneEl.matches('.s_references_carousel .s_references_carousel_item img')) {
            // Remove the cloned img element
            cloneEl.remove();

            // Clone the li.item instead
            const liItemEl = originalEl._cloneTarget;
            const clonedLiEl = liItemEl.cloneNode(true);

            // Insert the cloned li at the end of the list
            const listEl = liItemEl.closest('.s_references_carousel_list');
            if (listEl) {
                listEl.appendChild(clonedLiEl);
            }

            // Update the position and quantity
            const sliderEl = clonedLiEl.closest('.s_references_carousel_slider');
            if (sliderEl) {
                const itemEls = sliderEl.querySelectorAll('.s_references_carousel_item');
                // Update the position of the cloned element
                clonedLiEl.style.setProperty('--position', itemEls.length);
                // Update the quantity on the slider
                sliderEl.style.setProperty('--quantity', itemEls.length);
            }

            // Clean up the temporary property
            delete originalEl._cloneTarget;
        } else if (cloneEl.matches('.s_references_carousel .s_references_carousel_item')) {
            // Normal case: we cloned a li.item element directly
            const sliderEl = cloneEl.closest('.s_references_carousel_slider');
            if (sliderEl) {
                const itemEls = sliderEl.querySelectorAll('.s_references_carousel_item');
                // Update the position of the cloned element
                cloneEl.style.setProperty('--position', itemEls.length);
                // Update the quantity on the slider
                sliderEl.style.setProperty('--quantity', itemEls.length);
            }
        }
    }

    onRemove(removedEl) {
        // If we removed a li.item element, update the positions and quantity
        if (removedEl && removedEl.matches('.s_references_carousel .s_references_carousel_item')) {
            const sliderEl = removedEl.closest('.s_references_carousel_slider');
            if (sliderEl) {
                const remainingItemEls = sliderEl.querySelectorAll('.s_references_carousel_item');

                // Update positions of all remaining items
                remainingItemEls.forEach((itemEl, index) => {
                    itemEl.style.setProperty('--position', index + 1);
                });

                // Update the quantity on the slider
                sliderEl.style.setProperty('--quantity', remainingItemEls.length);
            }
        }
    }
}

registry.category("website-plugins").add("referencesCarouselOption", ReferencesCarouselOptionPlugin);
