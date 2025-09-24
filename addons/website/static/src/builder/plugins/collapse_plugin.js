import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class CollapsePlugin extends Plugin {
    static id = "collapse";

    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        on_cloned_handlers: this.onCloned.bind(this),
        dropzone_selector: [
            {
                selector: ".accordion-item",
                dropLockWithin: ".accordion",
            },
        ],
        is_movable_selector: {
            selector: ".s_accordion .accordion-item",
            direction: "vertical",
            noScroll: true,
        },
    };

    setup() {
        this.time = new Date().getTime();
        this.body = this.document.body;
    }

    onSnippetDropped({ snippetEl }) {
        const accordionItemsEls = snippetEl.querySelectorAll(".accordion > .accordion-item");
        accordionItemsEls.forEach((accordionItemEl) => {
            this.createIDs(accordionItemEl);
        });
    }

    onCloned({ cloneEl }) {
        const arrayOfAccordionItemEls = cloneEl.matches(".accordion > .accordion-item")
            ? [cloneEl]
            : [...cloneEl.querySelectorAll(".accordion > .accordion-item")];

        for (const accordionItemEl of arrayOfAccordionItemEls) {
            this.createIDs(accordionItemEl);
        }
    }

    createIDs(editingElement) {
        const accordionEl = editingElement.closest(".accordion");
        const accordionBtnEl = editingElement.querySelector(".accordion-button");
        const accordionContentEl = editingElement.querySelector('[role="region"]');

        const setUniqueId = (el, label) => {
            let elemId = el.id;
            if (!elemId || this.body.querySelectorAll(`#${elemId}`).length > 1) {
                do {
                    this.time++;
                    elemId = `${label}${this.time}`;
                } while (this.body.querySelector(`#${elemId}`));
                el.id = elemId;
            }
            return elemId;
        };

        const accordionId = setUniqueId(accordionEl, "myCollapse");
        accordionContentEl.dataset.bsParent = `#${accordionId}`;

        const contentId = setUniqueId(accordionContentEl, "myCollapseTab");
        accordionBtnEl.dataset.bsTarget = `#${contentId}`;
        accordionBtnEl.setAttribute("aria-controls", contentId);

        const buttonId = setUniqueId(accordionBtnEl, "myCollapseBtn");
        accordionContentEl.setAttribute("aria-labelledby", buttonId);
    }
}

registry.category("website-plugins").add(CollapsePlugin.id, CollapsePlugin);
