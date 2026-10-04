import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { useKeyboardReorder } from "@html_builder/utils/keyboard_reorder";
import { onWillStart, signal } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useSortable } from "@web/core/utils/sortable_owl";

export class SocialMediaLinks extends BaseOptionComponent {
    static id = "social_media_links";
    static template = "website.SocialMediaLinks";
    static dependencies = ["socialMediaOptionPlugin", "history", "operation"];
    rootRef = signal.ref();

    setup() {
        super.setup();

        const { prefillSocialMediaLinks } = this.dependencies.socialMediaOptionPlugin;
        onWillStart(async () => {
            // Prefill placeholder social media links for existing static
            // content (e.g., footer snippets) that are not added via drag and
            // drop.
            this.dependencies.operation.next(async () => {
                const prefilled = await prefillSocialMediaLinks(this.env.getEditingElement());
                if (prefilled) {
                    this.dependencies.history.commit({ areSocialMediaLinksPrefilled: true });
                }
            });
        });
        this.domState = useDomState((editingElement) => ({
            presentLinks: [...editingElement.querySelectorAll(":scope > a[href]")],
        }));

        this.nextId = 1001;
        this.ids = [];
        this.elIdsMap = new Map();
        this.idsElMap = new Map();

        this.keyboardReorder = useKeyboardReorder({
            getList: () => this.ids,
            insertAfter: (id, previousId) => this.moveLink(id, previousId),
            getHandle: (id) => this.rootRef()?.querySelector(`tr[data-id="${id}"] .o_drag_handle`),
        });

        useSortable({
            ref: this.rootRef,
            elements: "tr",
            handle: ".o_drag_handle",
            cursor: "grabbing",
            placeholderClasses: ["d-table-row"],

            onDrop: ({ previous, element }) => {
                this.moveLink(
                    parseInt(element.dataset.id),
                    previous ? parseInt(previous.dataset.id) : null
                );
            },
        });
    }

    /**
     * Moves a link after another one, in the panel and in the DOM.
     *
     * @param {number} elId
     * @param {number|null} previousId null = first position
     */
    moveLink(elId, previousId) {
        const oldIdx = this.ids.indexOf(elId);
        this.ids.splice(oldIdx, 1);
        const newIdx = previousId ? this.ids.indexOf(previousId) + 1 : 0;
        this.ids.splice(newIdx, 0, elId);
        const newNext = this.ids.slice(newIdx + 1).find((i) => this.idsElMap.get(i)?.isConnected);
        if (this.idsElMap.get(elId)?.isConnected) {
            this.dependencies.socialMediaOptionPlugin.reorderSocialMediaLink({
                editingElement: this.env.getEditingElement(),
                element: this.idsElMap.get(elId),
                elementAfter: this.idsElMap.get(newNext),
            });
            this.dependencies.history.commit();
        }
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
