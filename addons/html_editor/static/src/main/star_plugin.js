import { Plugin } from "@html_editor/plugin";
import {
    getAdjacentNextSiblings,
    getAdjacentPreviousSiblings,
} from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { _t } from "@web/core/l10n/translation";

export class StarPlugin extends Plugin {
    static name = "star";
    static dependencies = ["dom"];
    resources = {
        powerboxItems: [
            {
                name: _t("3 Stars"),
                description: _t("Insert a rating over 3 stars"),
                category: "widget",
                fontawesome: "fa-star-o",
                action: () => {
                    this.addStars(3);
                },
            },
            {
                name: _t("5 Stars"),
                description: _t("Insert a rating over 5 stars"),
                category: "widget",
                fontawesome: "fa-star",
                action: () => {
                    this.addStars(5);
                },
            },
        ],
    };

    setup() {
        this.addDomListener(this.editable, "pointerdown", this.onMouseDown);
    }

    onMouseDown(ev) {
        const node = ev.target;
        const isStar = (node) =>
            node.nodeType === Node.ELEMENT_NODE &&
            (node.classList.contains("fa-star") || node.classList.contains("fa-star-o"));
        if (
            isStar(node) &&
            node.parentElement &&
            node.parentElement.className.includes("o_stars")
        ) {
            const previousStars = getAdjacentPreviousSiblings(node, isStar);
            const nextStars = getAdjacentNextSiblings(node, isStar);
            if (nextStars.length || previousStars.length) {
                const shouldToggleOff =
                    node.classList.contains("fa-star") &&
                    (!nextStars[0] || !nextStars[0].classList.contains("fa-star"));
                for (const star of [...previousStars, node]) {
                    star.classList.toggle("fa-star-o", shouldToggleOff);
                    star.classList.toggle("fa-star", !shouldToggleOff);
                }
                for (const star of nextStars) {
                    star.classList.toggle("fa-star-o", true);
                    star.classList.toggle("fa-star", false);
                }
                this.dispatch("ADD_STEP");
            }
            ev.stopPropagation();
            ev.preventDefault();
        }
    }

    addStars(length) {
        const stars = Array.from({ length }, () => '<i class="fa fa-star-o"></i>').join("");
        const html = `\u200B<span contenteditable="false" class="o_stars">${stars}</span>\u200B`;
        this.shared.domInsert(parseHTML(this.document, html));
        this.dispatch("ADD_STEP");
    }
}
