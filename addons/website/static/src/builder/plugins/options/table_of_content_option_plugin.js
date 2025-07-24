import { applyFunDependOnSelectorAndExclude } from "@website/builder/plugins/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

/**
 * Returns the TOC id and the heading id from a header element.
 *
 * @param {HTMLElement} headingEl - A header element of the TOC.
 * @returns {Object}
 */
function getTocAndHeadingId(headingEl) {
    const match = /^table_of_content_heading_(\d+)_(\d+)$/.exec(
        headingEl && headingEl.getAttribute("id")
    );
    if (match) {
        return { tocId: parseInt(match[1]), headingId: parseInt(match[2]) };
    }
    return { tocId: 0, headingId: 0 };
}

class TableOfContentOptionPlugin extends Plugin {
    static id = "tableOfContentOption";
    static dependencies = ["clone", "remove"];
    resources = {
        builder_options: [
            {
                template: "website.TableOfContentOption",
                selector: ".s_table_of_content",
            },
            {
                template: "website.TableOfContentNavbarOption",
                selector: ".s_table_of_content_navbar_wrap",
            },
        ],
        builder_actions: {
            NavbarPositionAction,
        },
        normalize_handlers: this.normalize.bind(this),
        // Prevent dropping a table of content inside another table of content.
        dropzone_selector: {
            selector: ".s_table_of_content",
            excludeAncestor: ".s_table_of_content",
        },
        // Only allow moving main parts of the table of content by using arrows.
        is_draggable_handlers: (el) => {
            if (
                el.matches(
                    ".s_table_of_content .s_table_of_content_navbar_wrap, .s_table_of_content .s_table_of_content_main"
                )
            ) {
                return false;
            }
            return true;
        },
        is_unremovable_selector: ".s_table_of_content_navbar_wrap, .s_table_of_content_main",
        force_not_editable_selector: ".s_table_of_content_navbar",
    };

    normalize(root) {
        applyFunDependOnSelectorAndExclude(this.updateTableOfContentNavbar.bind(this), root, {
            selector: ".s_table_of_content_main",
        });
    }

    updateTableOfContentNavbar(tableOfContentMain) {
        const tableOfContent = tableOfContentMain.closest(".s_table_of_content");
        const tableOfContentNavbar = tableOfContent.querySelector(".s_table_of_content_navbar");
        const currentNavbarItems = [...tableOfContentNavbar.children].map((el) => ({
            title: el.textContent,
            href: el.getAttribute("href"),
        }));

        if (tableOfContentMain.children.length === 0) {
            // Remove the table of content if empty content.
            this.dependencies.remove.removeElement(tableOfContent)
            return;
        }

        const targetedElements = "h1, h2";
        const currentHeadingItems = [...tableOfContentMain.querySelectorAll(targetedElements)]
            .filter((el) => !el.closest(".o_snippet_desktop_invisible"))
            .map((el) => ({ title: el.textContent, id: `#${el.id}`, el }));

        const headingHasChanged =
            currentNavbarItems.length !== currentHeadingItems.length ||
            currentNavbarItems.some(
                (item, i) =>
                    item.title !== currentHeadingItems[i].title ||
                    item.href !== currentHeadingItems[i].id
            );

        const areVisibilityIdsEqual = currentHeadingItems.every(({ el }) => {
            const visibilityId = el.closest("section").getAttribute("data-visibility-id");
            const matchingLinkEl = tableOfContentNavbar.querySelector(
                `a[href="#${el.getAttribute("id")}"]`
            );
            const matchingLinkVisibilityId = matchingLinkEl
                ? matchingLinkEl.getAttribute("data-visibility-id")
                : null;
            // Check if visibilityId matches matchingLinkVisibilityId or both
            // are null/undefined
            return visibilityId === matchingLinkVisibilityId;
        });

        const firstHeadingEl = currentHeadingItems[0]?.el;
        let tocId = firstHeadingEl ? getTocAndHeadingId(firstHeadingEl).tocId : 0;
        const tocEls = this.editable.querySelectorAll("[data-snippet='s_table_of_content']");
        const otherTocEls = [...tocEls].filter((tocEl) => tocEl !== tableOfContent);
        const otherTocIds = otherTocEls.map((tocEl) => {
            const firstHeadingEl = tocEl.querySelector(targetedElements);
            return getTocAndHeadingId(firstHeadingEl).tocId;
        });

        let duplicateTocId = false;
        if (!tocId || otherTocIds.includes(tocId)) {
            tocId = 1 + Math.max(0, ...otherTocIds);
            duplicateTocId = true;
        }

        if (!headingHasChanged && areVisibilityIdsEqual && !duplicateTocId) {
            return;
        }

        const headingIds = currentHeadingItems.map(({ el }) => getTocAndHeadingId(el).headingId);
        let maxHeadingIds = Math.max(0, ...headingIds);

        tableOfContentNavbar.textContent = "";
        const uniqueHeadingIds = new Set();
        for (const { title, el } of currentHeadingItems) {
            let { headingId } = getTocAndHeadingId(el);
            if (headingId) {
                // Reset headingId on duplicate.
                if (uniqueHeadingIds.has(headingId)) {
                    headingId = 0;
                } else {
                    uniqueHeadingIds.add(headingId);
                }
            }
            if (!headingId) {
                maxHeadingIds += 1;
                headingId = maxHeadingIds;
            }
            const tocHeadingId = `table_of_content_heading_${tocId}_${headingId}`;

            const itemEl = this.document.createElement("a");
            itemEl.textContent = title;
            itemEl.setAttribute("href", `#${tocHeadingId}`);
            itemEl.className =
                "table_of_content_link list-group-item list-group-item-action py-2 border-0 rounded-0";
            tableOfContentNavbar.appendChild(itemEl);

            el.setAttribute("id", tocHeadingId);
        }
    }
}

export class NavbarPositionAction extends BuilderAction {
    static id = "navbarPosition";
    isApplied({ editingElement: navbarWrapEl, params: { mainParam: position } }) {
        if (navbarWrapEl.classList.contains("s_table_of_content_horizontal_navbar")) {
            return position === "top";
        } else {
            const mainContent = navbarWrapEl.parentNode.querySelector(".s_table_of_content_main");
            const previousSibling = navbarWrapEl.previousElementSibling;

            return (previousSibling === mainContent ? "right" : "left") === position;
        }
    }
    apply({ editingElement: navbarWrapEl, params: { mainParam: position } }) {
        const mainContentEl = navbarWrapEl.parentElement.querySelector(".s_table_of_content_main");
        const navbarEl = navbarWrapEl.querySelector(".s_table_of_content_navbar");

        if (position === "top" || position === "left") {
            const previousSibling = navbarWrapEl.previousElementSibling;
            if (previousSibling) {
                previousSibling.parentNode.insertBefore(navbarWrapEl, previousSibling);
            }
        }
        if (position === "left" || position === "right") {
            navbarWrapEl.classList.add("s_table_of_content_vertical_navbar", "col-lg-3");
            mainContentEl.classList.add("col-lg-9");
        }
        if (position === "right") {
            const nextSibling = navbarWrapEl.nextElementSibling;
            if (nextSibling) {
                nextSibling.parentNode.insertBefore(navbarWrapEl, nextSibling.nextSibling);
            }
        }
        if (position === "top") {
            navbarWrapEl.classList.add("s_table_of_content_horizontal_navbar", "col-lg-12");
            navbarEl.classList.add("list-group-horizontal-md");
            mainContentEl.classList.add("col-lg-12");
        }
    }
    clean({ editingElement: navbarWrapEl, params: { mainParam: position } }) {
        const mainContentEl = navbarWrapEl.parentElement.querySelector(".s_table_of_content_main");
        const navbarEl = navbarWrapEl.querySelector(".s_table_of_content_navbar");

        if (position === "top") {
            navbarWrapEl.classList.remove("s_table_of_content_horizontal_navbar", "col-lg-12");
            mainContentEl.classList.remove("col-lg-12");
            navbarEl.classList.remove("list-group-horizontal-md");
        }

        if (position === "left" || position === "right") {
            navbarWrapEl.classList.remove("s_table_of_content_vertical_navbar", "col-lg-3");
            mainContentEl.classList.remove("col-lg-9");
        }
    }
}

registry.category("website-plugins").add(TableOfContentOptionPlugin.id, TableOfContentOptionPlugin);
