import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { signal } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useSortable } from "@web/core/utils/sortable_owl";

const itemsSelector =
    ".s_references_carousel_marquee_item:not(.s_references_carousel_marquee_item_clone) > .s_references_carousel_item";

/**
 * Lists the logos of the carousel in the options panel, each with a preview,
 * to replace, remove or reorder them without reaching them in the page.
 */
export class ReferencesCarouselLogos extends BaseOptionComponent {
    static id = "references_carousel_logos";
    static template = "website.ReferencesCarouselLogos";
    static dependencies = ["referencesCarouselOption", "history"];
    rootRef = signal.ref();

    setup() {
        super.setup();
        this.domState = useDomState((editingElement) => ({
            items: [...editingElement.querySelectorAll(itemsSelector)].map((itemEl, index) => {
                const imgEl = itemEl.querySelector("img");
                const src = imgEl?.getAttribute("src") || "";
                // The key changes with the position and the image so that
                // the rows (and their `applyTo`) are rebuilt after a reorder
                // or a replacement.
                return { key: `${index}-${src}`, position: index + 1, src };
            }),
        }));

        useSortable({
            ref: this.rootRef,
            elements: ".o_references_carousel_logo",
            handle: ".o_drag_handle",
            cursor: "grabbing",
            onDrop: ({ element, next }) => {
                const itemEls = [...this.env.getEditingElement().querySelectorAll(itemsSelector)];
                const itemEl = itemEls[element.dataset.position - 1];
                const nextItemEl = next ? itemEls[next.dataset.position - 1] : null;
                if (!itemEl || nextItemEl === itemEl.nextElementSibling) {
                    return;
                }
                this.dependencies.referencesCarouselOption.reorderItem(itemEl, nextItemEl);
                this.dependencies.history.commit();
            },
        });
    }
}

registry.category("website-options").add(ReferencesCarouselLogos.id, ReferencesCarouselLogos);
