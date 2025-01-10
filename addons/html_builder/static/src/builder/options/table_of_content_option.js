import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * Returns the TOC id and the heading id from a header element.
 *
 * @param {HTMLElement} headingEl - A header element of the TOC.
 * @returns {Object}
 */
function getTocAndHeadingId(headingEl) {
    const match = /^table_of_content_heading_(\d+)_(\d+)$/.exec(headingEl.getAttribute("id"));
    if (match) {
        return { tocId: parseInt(match[1]), headingId: parseInt(match[2]) };
    }
    return { tocId: 0, headingId: 0 };
}

class TableOfContentOptionPlugin extends Plugin {
    static id = "TableOfContentOptionPlugin";
    static dependencies = ["clone"];
    resources = {
        builder_options: [
            {
                template: "html_builder.TableOfContentOption",
                selector: ".s_table_of_content",
            },
        ],
        builder_actions: this.getActions(),
        normalize_handlers: this.normalize.bind(this),
        clean_for_save_handlers: ({ root }) => {
            for (const element of root.querySelectorAll(".s_table_of_content_navbar")) {
                element.removeAttribute("contenteditable");
            }
        },
    };

    getActions() {
        return {
            // Should be move in a more generic plugin replace MultipleItems
            addItem: {
                apply: ({ editingElement, param: itemSelector }) => {
                    const itemEl = editingElement.querySelector(itemSelector);
                    this.dependencies.clone.cloneElement(itemEl);
                },
            },
        };
    }

    normalize(root) {
        for (const navbar of root.querySelectorAll(".s_table_of_content_navbar")) {
            navbar.setAttribute("contenteditable", "false");
        }
        const tableOfContentMain =
            root.closest(".s_table_of_content_main") ||
            root.querySelector(".s_table_of_content_main");
        if (tableOfContentMain) {
            this.updateTableOfContentNavbar(tableOfContentMain);
        }
    }

    updateTableOfContentNavbar(tableOfContentMain) {
        const tableOfContent = tableOfContentMain.closest(".s_table_of_content");
        const tableOfContentNavbar = tableOfContent.querySelector(".s_table_of_content_navbar");
        const currentNavbarItems = [...tableOfContentNavbar.children].map((el) => ({
            title: el.textContent,
            href: el.getAttribute("href"),
        }));

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

        if (!headingHasChanged && areVisibilityIdsEqual) {
            return;
        }

        const firstHeadingEl = currentHeadingItems[0]?.el;
        let tocId = firstHeadingEl ? getTocAndHeadingId(firstHeadingEl).tocId : 0;
        const tocEls = this.editable.querySelectorAll("[data-snippet='s_table_of_content']");
        const otherTocEls = [...tocEls].filter((tocEl) => tocEl !== tableOfContent);
        const otherTocIds = otherTocEls.map((tocEl) => {
            const firstHeadingEl = tocEl.querySelector(targetedElements);
            return getTocAndHeadingId(firstHeadingEl).tocId;
        });
        if (!tocId || otherTocIds.includes(tocId)) {
            tocId = 1 + Math.max(0, ...otherTocIds);
        }
        const headingIds = currentHeadingItems.map(({ el }) => getTocAndHeadingId(el).headingId);
        let maxHeadingIds = Math.max(0, ...headingIds);

        tableOfContentNavbar.innerHTML = "";
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
registry.category("website-plugins").add(TableOfContentOptionPlugin.id, TableOfContentOptionPlugin);
