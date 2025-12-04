import { Plugin } from "@html_editor/plugin";
import { fillEmpty, fillShrunkPhrasingParent } from "@html_editor/utils/dom";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { withSequence } from "@html_editor/utils/resource";
import { htmlEscape } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { closestBlock } from "@html_editor/utils/blocks";
import { isEmptyBlock, isParagraphRelatedElement } from "../utils/dom_info";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

function isAvailable(selection) {
    return (
        isHtmlContentSupported(selection) &&
        !closestElement(selection.anchorNode, ".o_editor_banner")
    );
}

/**
 * @typedef { Object } BannerShared
 * @property { BannerPlugin['insertBanner'] } insertBanner
 */

export class BannerPlugin extends Plugin {
    static id = "banner";
    // sanitize plugin is required to handle `contenteditable` attribute.
    static dependencies = ["baseContainer", "history", "dom", "emoji", "selection", "sanitize"];
    static shared = ["insertBanner"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "banner_info",
                title: _t("Banner Info"),
                description: _t("Insert an info banner"),
                icon: "fa-info-circle",
                isAvailable,
                run: () => {
                    this.insertBanner(_t("Banner Info"), "💡", "info");
                },
            },
            {
                id: "banner_success",
                title: _t("Banner Success"),
                description: _t("Insert a success banner"),
                icon: "fa-check-circle",
                isAvailable,
                run: () => {
                    this.insertBanner(_t("Banner Success"), "✅", "success");
                },
            },
            {
                id: "banner_warning",
                title: _t("Banner Warning"),
                description: _t("Insert a warning banner"),
                icon: "fa-exclamation-triangle",
                isAvailable,
                run: () => {
                    this.insertBanner(_t("Banner Warning"), "⚠️", "warning");
                },
            },
            {
                id: "banner_danger",
                title: _t("Banner Danger"),
                description: _t("Insert a danger banner"),
                icon: "fa-exclamation-circle",
                isAvailable,
                run: () => {
                    this.insertBanner(_t("Banner Danger"), "❌", "danger");
                },
            },
            {
                id: "banner_monospace",
                title: _t("Monospace"),
                description: _t("Insert a monospace banner"),
                icon: "fa-laptop",
                isAvailable,
                run: () => {
                    this.insertBanner(
                        _t("Monospace Banner"),
                        undefined,
                        "secondary",
                        "font-monospace"
                    );
                },
            },
        ],
        powerbox_categories: withSequence(20, { id: "banner", name: _t("Banner") }),
        powerbox_items: [
            {
                commandId: "banner_info",
                categoryId: "banner",
            },
            {
                commandId: "banner_success",
                categoryId: "banner",
            },
            {
                commandId: "banner_warning",
                categoryId: "banner",
            },
            {
                commandId: "banner_danger",
                categoryId: "banner",
            },
            {
                commandId: "banner_monospace",
                categoryId: "banner",
            },
        ],
        power_buttons_visibility_predicates: ({ anchorNode }) =>
            !closestElement(anchorNode, ".o_editor_banner"),
        move_node_blacklist_selectors: ".o_editor_banner *",
        move_node_whitelist_selectors: ".o_editor_banner",

        /** Overrides */
        delete_backward_overrides: this.handleDeleteBackward.bind(this),
        delete_backward_word_overrides: this.handleDeleteBackward.bind(this),
    };

    setup() {
        this.addDomListener(this.editable, "click", (e) => {
            if (e.target.classList.contains("o_editor_banner_icon")) {
                this.onBannerEmojiChange(e.target);
            }
        });
    }

    insertBanner(title, emoji, alertClass, containerClass = "", contentClass = "") {
        containerClass = containerClass ? `${containerClass} ` : "";
        contentClass = contentClass ? `${contentClass} ` : "";

        const selection = this.dependencies.selection.getEditableSelection();
        const blockEl = closestBlock(selection.anchorNode);
        let baseContainer;
        if (isParagraphRelatedElement(blockEl)) {
            baseContainer = this.document.createElement(blockEl.nodeName);
            baseContainer.append(...blockEl.childNodes);
        } else if (blockEl.nodeName === "LI") {
            baseContainer = this.dependencies.baseContainer.createBaseContainer();
            baseContainer.append(...blockEl.childNodes);
            fillShrunkPhrasingParent(blockEl);
        } else {
            baseContainer = this.dependencies.baseContainer.createBaseContainer();
            fillShrunkPhrasingParent(baseContainer);
        }
        const baseContainerHtml = baseContainer.outerHTML;
        const emojiHtml = emoji
            ? `<i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="${htmlEscape(
                  title
              )}">${emoji}</i>`
            : "";
        const bannerElement = parseHTML(
            this.document,
            `<div class="${containerClass}o_editor_banner user-select-none o-contenteditable-false ${
                emoji ? "lh-1 " : ""
            }d-flex align-items-center alert alert-${alertClass} pb-0 pt-3" data-oe-role="status">
                ${emojiHtml}
                <div class="${contentClass}o_editor_banner_content o-contenteditable-true w-100 px-3">
                    ${baseContainerHtml}
                </div>
            </div>`
        ).childNodes[0];
        this.dependencies.dom.insert(bannerElement);
        this.dependencies.selection.setCursorEnd(
            bannerElement.querySelector(`.o_editor_banner_content > ${baseContainer.tagName}`)
        );
        this.dependencies.history.addStep();
    }

    onBannerEmojiChange(iconElement) {
        this.dependencies.emoji.showEmojiPicker({
            target: iconElement,
            onSelect: (emoji) => {
                iconElement.textContent = emoji;
                this.dependencies.history.addStep();
            },
        });
    }

    // Transform empty banner into base container on backspace.
    handleDeleteBackward(range) {
        const editorBannerContent = closestElement(range.endContainer, ".o_editor_banner_content");
        if (!isEmptyBlock(editorBannerContent)) {
            return;
        }
        const bannerElement = closestElement(editorBannerContent, ".o_editor_banner");
        const baseContainer = this.dependencies.baseContainer.createBaseContainer();
        fillEmpty(baseContainer);
        bannerElement.replaceWith(baseContainer);
        this.dependencies.selection.setCursorStart(baseContainer);
        return true;
    }
}
