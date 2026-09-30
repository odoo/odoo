import { useDomState, BaseOptionComponent } from "@html_builder/core/utils";
import { onWillStart, useRef, useState } from "@odoo/owl";
import { useSortable } from "@web/core/utils/sortable_owl";

export class SocialMediaLinks extends BaseOptionComponent {
    static template = "website.SocialMediaLinks";
    static dependencies = ["socialMediaOptionPlugin", "history"];
    static selector = ".s_social_media";

    setup() {
        super.setup();

        const { getRecordedSocialMediaNames, reorderSocialMediaLink } =
            this.dependencies.socialMediaOptionPlugin;

        onWillStart(async () => {
            this.recordedSocialMediaNames = await getRecordedSocialMediaNames();
        });
        this.rootRef = useRef("root");
        this.domState = useDomState((editingElement) => ({
            presentLinks: [...editingElement.querySelectorAll(":scope > a[href]")].map(
                (element) => ({
                    element,
                    media: element.attributes.href.value.split("/website/social/")[1],
                })
            ),
        }));

        this.nextId = 1001;
        this.ids = [];
        this.elIdsMap = new Map();
        this.idsElMap = new Map();
        this.idsMediaMap = new Map();
        this.mediaIdsMap = new Map();

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
     * Each item has at least one of `domPosition` or `media`
     * @typedef { Object } SocialMediaLinkItem
     * @property { String } fabricatedKey a key that combines the `id` and the `domPosition` (this is a hack to trigger rebuild when domPosition changes, because `applyTo does not correctly support props updates)
     * @property { int } id An arbitrary number to identify an item
     * @property { int } [domPosition] The position of the link in the children list (if the item has a link in the dom), starting from 1 (to use `:nth-` selector)
     * @property { string } [media] The name of the recorded social media (if the item is editing a link from the orm)
     */

    /**
     * Builds the list of items by reconciling what is present in the dom with what was previously computed
     * @returns { SocialMediaLinkItem[] }
     */
    computeItems() {
        const missingRecordedSocialMediaNames = new Set(this.recordedSocialMediaNames);
        const idsLookUp = new Map(this.ids.map((id, i) => [id, i]));
        const idsInDom = new Set();
        const itemsFromDom = this.domState.presentLinks.map(({ element, media }, domPosition) => {
            let id = this.elIdsMap.get(element);
            if (!id) {
                const idBasedOnMedia = this.mediaIdsMap.get(media);
                if (!idsInDom.has(idBasedOnMedia)) {
                    id = idBasedOnMedia;
                }
            }
            if (!id) {
                id = this.nextId++;
            }
            idsInDom.add(id);
            if (media) {
                missingRecordedSocialMediaNames.delete(media);
            }
            return { element, media, id, domPosition: domPosition + 1 };
        });
        const items = [];
        const addRecordedSocialMediaAtStartOfSlice = (slice) => {
            for (const id of slice) {
                if (idsInDom.has(id)) {
                    break;
                }
                const media = this.idsMediaMap.get(id);
                if (media) {
                    items.push({ id, media });
                    missingRecordedSocialMediaNames.delete(media);
                }
            }
        };
        addRecordedSocialMediaAtStartOfSlice(this.ids);
        for (const item of itemsFromDom) {
            items.push(item);
            const start = idsLookUp.get(item.id);
            if (start !== undefined) {
                addRecordedSocialMediaAtStartOfSlice(this.ids.slice(start + 1));
            }
        }
        for (const media of missingRecordedSocialMediaNames) {
            items.push({ id: this.nextId++, media });
        }

        this.ids = [];
        this.elIdsMap = new Map();
        this.idsMediaMap = new Map();

        for (const item of items) {
            this.ids.push(item.id);
            if (item.element) {
                this.elIdsMap.set(item.element, item.id);
                this.idsElMap.set(item.id, item.element);
            }
            if (item.media) {
                this.idsMediaMap.set(item.id, item.media);
                this.mediaIdsMap.set(item.media, item.id);
            }
        }
        let elementAfter = null;
        for (let i = items.length - 1; i >= 0; i--) {
            items[i].nextLink = elementAfter;
            // This fabricated key is a hack. It is used as `t-key` in the component instead of the id in order to force re-creation of the components if the domPosition changes (this re-creation is a workaround for the applyTo that are not correctly updated)
            items[i].fabricatedKey = `${items[i].id}+${items[i].domPosition}`;
            if (items[i].element) {
                elementAfter = items[i].element;
                delete items[i].element;
            }
        }

        return items;
    }
}
