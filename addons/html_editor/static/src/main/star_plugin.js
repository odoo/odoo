import { Plugin } from "@html_editor/plugin";
import { parseHTML } from "@html_editor/utils/html";
import { _t } from "@web/core/l10n/translation";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

export class StarPlugin extends Plugin {
    static id = "star";
    static dependencies = ["dom", "history"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "addStars",
                title: _t("Stars"),
                description: _t("Insert a rating"),
                icon: "star",
                icon_class: "oi-filled",
                run: this.addStars.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        powerbox_items: [
            {
                title: _t("3 Stars"),
                description: _t("Insert a rating over 3 stars"),
                categoryId: "widget",
                icon: "star",
                commandId: "addStars",
                commandParams: { length: 3 },
            },
            {
                title: _t("5 Stars"),
                description: _t("Insert a rating over 5 stars"),
                categoryId: "widget",
                commandId: "addStars",
                commandParams: { length: 5 },
            },
        ],
        selectors_for_feff_providers: () => ".o_stars",
    };

    setup() {
        this.addDomListener(this.editable, "pointerdown", this.onMouseDown);
    }

    onMouseDown(ev) {
        const node = ev.target;
        const isStar = (node) =>
            node.nodeType === Node.ELEMENT_NODE && node.dataset.icon === "star";
        if (
            isStar(node) &&
            node.parentElement &&
            node.parentElement.className.includes("o_stars")
        ) {
            const allStars = Array.from(node.parentElement.childNodes).filter(isStar);
            const currentStarIndex = allStars.indexOf(node);
            const previousStars = allStars.slice(0, currentStarIndex);
            const nextStars = allStars.slice(currentStarIndex + 1);
            if (nextStars.length || previousStars.length) {
                const shouldToggleOff =
                    node.classList.contains("oi-filled") &&
                    (!nextStars[0] || !nextStars[0].classList.contains("oi-filled"));
                for (const star of [...previousStars, node]) {
                    star.classList.toggle("oi-filled", !shouldToggleOff);
                }
                for (const star of nextStars) {
                    star.classList.toggle("oi-filled", false);
                }
                this.dependencies.history.commit();
            }
            ev.stopPropagation();
            ev.preventDefault();
        }
    }

    addStars({ length }) {
        const stars = Array(length).fill('<i class="oi" data-icon="star"></i>').join("");
        const html = `<span contenteditable="false" class="o_stars">${stars}</span>`;
        this.dependencies.dom.insert(parseHTML(this.document, html));
        this.dependencies.history.commit();
    }
}
