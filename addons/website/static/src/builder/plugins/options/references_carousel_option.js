import { useDomState, BaseOptionComponent } from "@html_builder/core/utils";
import { useOperation } from "@html_builder/core/operation_plugin";
import { useRef, useState } from "@odoo/owl";
import { useSortable } from "@web/core/utils/sortable_owl";

export class ReferencesCarouselImagesOption extends BaseOptionComponent {
    static template = "website.ReferencesCarouselImagesOption";
    static props = {};

    setup() {
        super.setup();
        this.callOperation = useOperation();
        this.rootRef = useRef("root");
        this.domState = useDomState((editingElement) => {
            const slider = editingElement.querySelector('.slider');
            const items = [...slider.querySelectorAll('.item')];
            return {
                items: items.map((item, index) => ({
                    element: item,
                    img: item.querySelector('img'),
                    position: index + 1,
                    src: item.querySelector('img')?.src || '',
                })),
                quantity: items.length,
            };
        });

        this.nextId = 1001;
        this.ids = [];
        this.elIdsMap = new Map();
        this.idsElMap = new Map();

        // hack to trigger the rebuild
        this.reorderTriggered = useState({ trigger: 0 });

        useSortable({
            ref: this.rootRef,
            elements: "tr",
            handle: ".o_drag_handle",
            cursor: "grabbing",
            placeholderClasses: ["d-table-row"],

            onDrop: ({ next, element }) => {
                const elId = parseInt(element.dataset.id);
                const nextId = next?.dataset.id;

                const oldIdx = this.ids.findIndex((id) => id === elId);
                this.ids.splice(oldIdx, 1);
                let idx = this.ids.findIndex((id) => id == nextId);
                if (0 <= idx) {
                    this.ids.splice(idx, 0, elId);
                } else {
                    idx = this.ids.length;
                    this.ids.push(elId);
                }

                const itemElement = this.idsElMap.get(elId);
                const nextElement = nextId ? this.idsElMap.get(parseInt(nextId)) : null;
                
                if (itemElement?.isConnected) {
                    this.reorderImage(itemElement, nextElement);
                }

                // hack to trigger the rebuild
                this.reorderTriggered.trigger++;
            },
        });
    }

    /**
     * Builds the list of items by reconciling what is present in the dom with what was previously computed
     * @returns { Object[] }
     */
    computeItems() {
        const items = [];
        
        for (const [index, item] of this.domState.items.entries()) {
            let id = this.elIdsMap.get(item.element);
            if (!id) {
                id = this.nextId++;
            }
            
            items.push({
                id,
                element: item.element,
                img: item.img,
                position: index + 1,
                src: item.src,
                fabricatedKey: `${id}+${index}`,
            });
        }

        // Rebuild maps
        this.ids = [];
        this.elIdsMap = new Map();
        this.idsElMap = new Map();

        for (const item of items) {
            this.ids.push(item.id);
            this.elIdsMap.set(item.element, item.id);
            this.idsElMap.set(item.id, item.element);
        }

        return items;
    }



    reorderImage(element, elementAfter) {
        this.callOperation(async () => {
            const editingElement = this.env.getEditingElement();
            const list = editingElement.querySelector('.slider .list');
            
            if (elementAfter) {
                list.insertBefore(element, elementAfter);
            } else {
                list.appendChild(element);
            }
            
            // Update positions after reordering
            const items = list.querySelectorAll('.item');
            items.forEach((item, index) => {
                item.style.setProperty('--position', index + 1);
            });
        });
    }

    selectImage(position) {
        // Find the corresponding image in the carousel and select it for editing
        const editingElement = this.env.getEditingElement();
        const targetImage = editingElement.querySelector(`li.item:nth-of-type(${position}) img`);
        if (targetImage) {
            // Use the builder's updateContainers method to select the image
            this.env.editor.shared.builderOptions.updateContainers(targetImage);
        }
    }
}

export class ReferencesCarouselOption extends BaseOptionComponent {
    static template = "website.ReferencesCarouselOption";
    static components = {
        ReferencesCarouselImagesOption,
    };
    static props = {};
} 
 