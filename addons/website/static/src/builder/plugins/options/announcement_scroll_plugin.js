import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { EDITOR_MUTATION_TYPES } from "@html_editor/core/dom_observer_plugin";
import { closestElement, selectElements } from "@html_editor/utils/dom_traversal";
import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";

export class AnnouncementScrollPlugin extends Plugin {
    static id = "announcementScrollPlugin";
    static dependencies = ["dom"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        content_not_editable_selectors: ".s_announcement_scroll_marquee_container",
        content_editable_selectors: ".s_announcement_scroll_marquee_item",
    };
    setup() {
        applyFunDependOnSelectorAndExclude(this.updateTemplate.bind(this), this.editable, {
            selector: ".s_announcement_scroll_marquee_item.o_not_editable",
        });
    }

    updateTemplate(itemEl) {
        this.dependencies.dom.setTagName(itemEl, "p").remove("o_not_editable");
    }
}

export class AnnouncementScrollEditPlugin extends Plugin {
    static id = "announcementScrollEditPlugin";
    static dependencies = ["domObserver", "domReferenceMap"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        on_pending_mutations_staged_handlers: this.handleMutations.bind(this),
        normalize_processors: (root) => {
            applyFunDependOnSelectorAndExclude(this.copyToSibling.bind(this), root, {
                selector: ".s_announcement_scroll_marquee_item",
                exclude: ".s_announcement_scroll_marquee_item_clone",
            });
            return root;
        },
        on_selectionchange_handlers: (selection) =>
            this.dependencies.domObserver.ignore(() => this.onSelectionChange(selection)),
        clean_for_save_processors: (root) => {
            for (const el of selectElements(root, ".o_marquee_has_selection")) {
                el.classList.remove("o_marquee_has_selection");
                el.style.removeProperty("--marquee-intial-offset");
                el.style.removeProperty("--marquee-intial-item-size");
                el.style.removeProperty("--marquee-item-selected-index");
            }
            return root;
        },
    };

    handleMutations(mutations) {
        mutations
            .map((m) => {
                let nodeId = m.nodeId;
                // TODO: Wouldn't doing this only for "remove" be enough?
                if (
                    [EDITOR_MUTATION_TYPES.ADD, EDITOR_MUTATION_TYPES.REMOVE].includes(m.type) &&
                    m.parentNodeId
                ) {
                    nodeId = m.parentNodeId;
                }
                return closestElement(
                    this.dependencies.domReferenceMap.getNodeById(nodeId),
                    ".s_announcement_scroll_marquee_item"
                );
            })
            .filter(Boolean)
            .forEach((itemEl) => this.copyToSibling(itemEl));
    }
    copyToSibling(itemEl) {
        const targetEls = [
            ...itemEl.parentElement.querySelectorAll(".s_announcement_scroll_marquee_item"),
        ].filter((el) => el !== itemEl);
        for (const targetEl of targetEls) {
            if (targetEl.innerHTML !== itemEl.innerHTML) {
                targetEl.replaceChildren(...itemEl.cloneNode(true).childNodes);
            }
        }
    }

    onSelectionChange(selection) {
        const prevMarquee = this.editable.querySelector(".o_marquee_has_selection");
        const anchorNode = selection?.documentSelection?.anchorNode;
        const nextMarqueeEl =
            anchorNode && closestElement(anchorNode, ".s_announcement_scroll_marquee_container");
        const itemEl =
            anchorNode && closestElement(anchorNode, ".s_announcement_scroll_marquee_item");
        if (itemEl && prevMarquee === nextMarqueeEl) {
            const index = [...nextMarqueeEl.children].indexOf(itemEl);
            const prevIndex = parseInt(
                nextMarqueeEl.style.getPropertyValue("--marquee-item-selected-index")
            );
            if (index !== prevIndex) {
                const prevOffset = parseInt(
                    nextMarqueeEl.style.getPropertyValue("--marquee-intial-offset")
                );
                const initialSize = parseInt(
                    nextMarqueeEl.style.getPropertyValue("--marquee-intial-item-size")
                );
                nextMarqueeEl.style.setProperty(
                    "--marquee-intial-offset",
                    prevOffset - (index - prevIndex) * (initialSize - itemEl.offsetWidth)
                );
                nextMarqueeEl.style.setProperty("--marquee-item-selected-index", index);
            }
            const anchorOffset = selection.documentSelection.anchorOffset;
            this.adaptOffset({ marqueeEl: nextMarqueeEl, anchorNode, anchorOffset });
            return;
        }
        if (prevMarquee) {
            prevMarquee.classList.remove("o_marquee_has_selection");
            prevMarquee.style.removeProperty("--marquee-intial-offset");
            prevMarquee.style.removeProperty("--marquee-intial-item-size");
            prevMarquee.style.removeProperty("--marquee-item-selected-index");
        }
        if (itemEl) {
            const index = [...nextMarqueeEl.children].indexOf(itemEl);
            nextMarqueeEl.classList.add("o_marquee_has_selection");
            nextMarqueeEl.style.setProperty("--marquee-intial-offset", 0);
            nextMarqueeEl.style.setProperty("--marquee-intial-item-size", itemEl.offsetWidth);
            nextMarqueeEl.style.setProperty("--marquee-item-selected-index", index);

            // "reset" the time, because the duration of the cycle depends on
            // the size of the item. Thus, if time grows large, a small change
            // in the cycle's duration has a large impact on how far exactly
            // are we in the cycle. By reseting the time to a value lower than
            // a cycle, the impact is barely noticeable
            const duration = parseFloat(this.window.getComputedStyle(itemEl).animationDuration);
            for (const child of nextMarqueeEl.children) {
                for (const animation of child.getAnimations()) {
                    animation.currentTime = animation.currentTime % (duration * 1000);
                }
            }
        }
        if (nextMarqueeEl) {
            const anchorOffset = selection.documentSelection.anchorOffset;
            this.adaptOffset({ marqueeEl: nextMarqueeEl, anchorNode, anchorOffset });
        }
    }

    adaptOffset({ marqueeEl, anchorNode, anchorOffset }) {
        const range = new Range();
        range.setStart(anchorNode, anchorOffset);
        range.setEnd(anchorNode, anchorOffset);
        const pos = range.getBoundingClientRect().x;
        const maxPos = marqueeEl.getBoundingClientRect().width;
        const extraSpace = Math.min(20, maxPos / 2);
        let shift = 0;
        if (pos < 0) {
            shift = -pos + extraSpace;
        }
        if (pos > maxPos) {
            shift = maxPos - pos - extraSpace;
        }
        shift = Math.round(shift);
        if (shift !== 0) {
            const current = parseInt(marqueeEl.style.getPropertyValue("--marquee-intial-offset"));
            marqueeEl.style.setProperty("--marquee-intial-offset", current + shift);
        }
    }
}

registry.category("website-plugins").add(AnnouncementScrollPlugin.id, AnnouncementScrollPlugin);
registry
    .category("website-plugins")
    .add(AnnouncementScrollEditPlugin.id, AnnouncementScrollEditPlugin);
registry
    .category("translation-plugins")
    .add(AnnouncementScrollEditPlugin.id, AnnouncementScrollEditPlugin);
