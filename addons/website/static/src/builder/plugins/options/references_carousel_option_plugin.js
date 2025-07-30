import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ReferencesCarouselOption } from "./references_carousel_option";
import { BuilderAction } from "@html_builder/core/builder_action";

export class AddImageAction extends BuilderAction {
    static id = "addReferencesCarouselImage";
    
    apply({ editingElement }) {
        const slider = editingElement.querySelector('.slider');
        const list = slider.querySelector('.list');
        const items = list.querySelectorAll('.item');
        const newPosition = items.length + 1;
        
        // Create new item
        const newItem = document.createElement('li');
        newItem.className = 'item';
        newItem.style.setProperty('--position', newPosition);
        
        const img = document.createElement('img');
        img.src = '/web/image/website.s_reference_demo_image_1';
        img.className = 'img img-fluid';
        img.alt = '';
        
        newItem.appendChild(img);
        list.appendChild(newItem);
        
        // Update quantity after adding the item
        const updatedItems = list.querySelectorAll('.item');
        slider.style.setProperty('--quantity', updatedItems.length);
    }
}

export class RemoveImageAction extends BuilderAction {
    static id = "removeReferencesCarouselImage";
    
    apply({ editingElement }) {
        // editingElement is the targeted li.item when using applyTo
        // Navigate up to find the carousel container
        const carouselContainer = editingElement.closest('.s_references_carousel');
        if (!carouselContainer) {
            return;
        }
        
        const slider = carouselContainer.querySelector('.slider');
        const list = slider.querySelector('.list');
        const items = list.querySelectorAll('.item');
        
        if (items.length <= 1) {
            // Don't remove if it's the last image
            return;
        }
        
        // Remove the targeted item (editingElement is the li.item)
        editingElement.remove();
        
        // Update positions and quantity after removal
        const remainingItems = list.querySelectorAll('.item');
        remainingItems.forEach((item, index) => {
            item.style.setProperty('--position', index + 1);
        });
        
        slider.style.setProperty('--quantity', remainingItems.length);
    }
}

class ReferencesCarouselOptionPlugin extends Plugin {
    static id = "referencesCarouselOption";
    
    get resources() {
        return {
            builder_options: [
                {
                    OptionComponent: ReferencesCarouselOption,
                    selector: ".s_references_carousel",
                },
            ],
            builder_actions: {
                AddImageAction,
                RemoveImageAction,
            },
        };
    }
}

registry.category("website-plugins").add("referencesCarouselOption", ReferencesCarouselOptionPlugin);
