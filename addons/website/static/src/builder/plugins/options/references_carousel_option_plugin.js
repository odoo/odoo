import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { END } from "@html_builder/utils/option_sequence";
import { ReferencesCarouselOption } from "./references_carousel_option";

class ReferencesCarouselOptionPlugin extends Plugin {
    static id = "referencesCarouselOption";

    get resources() {
        return {
            builder_options: [
                withSequence(END, {
                    OptionComponent: ReferencesCarouselOption,
                    selector: ".s_references_carousel",
                }),
            ],
            on_will_clone_handlers: [this.onWillClone.bind(this)],
            on_cloned_handlers: [this.onCloned.bind(this)],
            on_remove_handlers: [this.onRemove.bind(this)],
            change_current_options_containers_listeners: [this.onSelectionChange.bind(this)],
        };
    }

    onSelectionChange(containers) {
        // Find all references carousels in the document
        const allReferencesCarousels = this.editable.querySelectorAll('.s_references_carousel');

        // Check if any of the selected containers is a references carousel
        const isReferencesCarouselSelected = containers.some(container => 
            container.element && container.element.matches('.s_references_carousel')
        );

        // Add or remove the 'snippet-selected' class to all references carousels
        allReferencesCarousels.forEach(carousel => {
            if (isReferencesCarouselSelected && containers.some(container => container.element === carousel)) {
                carousel.classList.add('snippet-selected');
            } else {
                carousel.classList.remove('snippet-selected');
            }
        });
    }

    onWillClone({ originalEl }) {
        // If the original element is an img inside a li.item, we need to redirect the clone
        // to target the li.item instead. We'll store this information for the clone operation.
        if (originalEl.matches('.s_references_carousel .item img')) {
            const liItem = originalEl.closest('.item');
            if (liItem) {
                // Store the target li element on the original img element for the clone operation
                originalEl._cloneTarget = liItem;
            }
        }
    }

    onCloned({ cloneEl, originalEl }) {
        // If we cloned an img element that had a _cloneTarget, we need to handle this specially
        if (originalEl._cloneTarget && cloneEl.matches('.s_references_carousel .item img')) {
            // Remove the cloned img element
            cloneEl.remove();

            // Clone the li.item instead
            const liItem = originalEl._cloneTarget;
            const clonedLi = liItem.cloneNode(true);

            // Insert the cloned li at the end of the list
            const list = liItem.closest('.list');
            if (list) {
                list.appendChild(clonedLi);
            }

            // Update the position and quantity
            const slider = clonedLi.closest('.slider');
            if (slider) {
                const items = slider.querySelectorAll('.item');
                // Update the position of the cloned element
                clonedLi.style.setProperty('--position', items.length);
                // Update the quantity on the slider
                slider.style.setProperty('--quantity', items.length);
            }

            // Clean up the temporary property
            delete originalEl._cloneTarget;
        } else if (cloneEl.matches('.s_references_carousel .item')) {
            // Normal case: we cloned a li.item element directly
            const slider = cloneEl.closest('.slider');
            if (slider) {
                const items = slider.querySelectorAll('.item');
                // Update the position of the cloned element
                cloneEl.style.setProperty('--position', items.length);
                // Update the quantity on the slider
                slider.style.setProperty('--quantity', items.length);
            }
        }
    }

    onRemove(removedEl) {
        // If we removed a li.item element, update the positions and quantity
        if (removedEl && removedEl.matches('.s_references_carousel .item')) {
            const slider = removedEl.closest('.slider');
            if (slider) {
                const remainingItems = slider.querySelectorAll('.item');

                // Update positions of all remaining items
                remainingItems.forEach((item, index) => {
                    item.style.setProperty('--position', index + 1);
                });

                // Update the quantity on the slider
                slider.style.setProperty('--quantity', remainingItems.length);
            }
        }
    }
}

registry.category("website-plugins").add("referencesCarouselOption", ReferencesCarouselOptionPlugin);
