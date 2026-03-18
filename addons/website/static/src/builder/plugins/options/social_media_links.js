import { useRef, useState } from "@web/owl2/utils";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useSortable } from "@web/core/utils/sortable_owl";

export class SocialMediaLinks extends BaseOptionComponent {
    static id = "social_media_links";
    static template = "website.SocialMediaLinks";
    static dependencies = ["socialMediaOptionPlugin", "history", "operation"];

    setup() {
        super.setup();

        const { reorderSocialMediaLink, prefillSocialMediaLinks } =
            this.dependencies.socialMediaOptionPlugin;
        onWillStart(async () => {
            // Prefill placeholder social media links for existing static
            // content (e.g., footer snippets) that are not added via drag and
            // drop.
            this.dependencies.operation.next(async () => {
                const prefilled = await prefillSocialMediaLinks(this.env.getEditingElement());
                if (prefilled) {
                    this.dependencies.history.addStep({ extraStepInfos: { prefill: true } });
                }
            });
        });
        this.rootRef = useRef("root");
        this.domState = useDomState((editingElement) => ({
            presentLinks: [...editingElement.querySelectorAll(":scope > a[href]")],
        }));

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
                const oldNext = this.ids
                    .slice(oldIdx)
                    .find((i) => this.idsElMap.get(i)?.isConnected);
                let idx = this.ids.findIndex((id) => id == nextId);
                if (0 <= idx) {
                    this.ids.splice(idx, 0, elId);
                } else {
                    idx = this.ids.length;
                    this.ids.push(elId);
                }
                const newNext = this.ids
                    .slice(idx + 1)
                    .find((i) => this.idsElMap.get(i)?.isConnected);

                if (this.idsElMap.get(elId)?.isConnected && oldNext !== newNext) {
                    reorderSocialMediaLink({
                        editingElement: this.env.getEditingElement(),
                        element: this.idsElMap.get(elId),
                        elementAfter: this.idsElMap.get(newNext),
                    });
                    this.dependencies.history.addStep();
                }

                // hack to trigger the rebuild
                this.reorderTriggered.trigger++;
            },
        });
    }

    /**
     * @typedef { Object } SocialMediaLinkItem
     * @property { String } fabricatedKey a key that combines the `id` and the `domPosition` (this is a hack to trigger rebuild when domPosition changes, because `applyTo does not correctly support props updates)
     * @property { int } id An arbitrary number to identify an item
     * @property { int } [domPosition] The position of the link in the children list (if the item has a link in the dom), starting from 1 (to use `:nth-` selector)
     */

    /**
     * Builds the list of items by reconciling what is present in the dom with what was previously computed
     * @returns { SocialMediaLinkItem[] }
     */
    computeItems() {
        const items = this.domState.presentLinks.map((element, domPosition) => {
            let id = this.elIdsMap.get(element);
            if (!id) {
                id = this.nextId++;
            }
            return { element, id, domPosition: domPosition + 1 };
        });

        this.ids = [];
        this.elIdsMap = new Map();

        for (const item of items) {
            this.ids.push(item.id);
            if (item.element) {
                this.elIdsMap.set(item.element, item.id);
                this.idsElMap.set(item.id, item.element);
            }
        }
        for (let i = items.length - 1; i >= 0; i--) {
            // This fabricated key is a hack. It is used as `t-key` in the component instead of the id in order to force re-creation of the components if the domPosition changes (this re-creation is a workaround for the applyTo that are not correctly updated)
            items[i].fabricatedKey = `${items[i].id}+${items[i].domPosition}`;
            if (items[i].element) {
                delete items[i].element;
            }
        }

        return items;
    }
}

registry.category("website-options").add(SocialMediaLinks.id, SocialMediaLinks);
