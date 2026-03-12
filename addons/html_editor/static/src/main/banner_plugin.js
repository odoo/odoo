import { Plugin } from "@html_editor/plugin";
import { fillShrunkPhrasingParent } from "@html_editor/utils/dom";
import { closestElement, descendants, selectElements } from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { withSequence } from "@html_editor/utils/resource";
import { htmlEscape } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { closestBlock } from "@html_editor/utils/blocks";
import { isEmptyBlock, isParagraphRelatedElement } from "../utils/dom_info";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

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
                isAvailable: (selection) =>
                    this.checkPredicates("is_banner_command_available_predicates", selection, "info") ?? true,
                run: () => {
                    this.insertBanner(_t("Banner Info"), "💡", "info");
                },
            },
            {
                id: "banner_success",
                title: _t("Banner Success"),
                description: _t("Insert a success banner"),
                icon: "fa-check-circle",
                isAvailable: (selection) =>
                    this.checkPredicates("is_banner_command_available_predicates", selection, "success") ?? true,
                run: () => {
                    this.insertBanner(_t("Banner Success"), "✅", "success");
                },
            },
            {
                id: "banner_warning",
                title: _t("Banner Warning"),
                description: _t("Insert a warning banner"),
                icon: "fa-exclamation-triangle",
                isAvailable: (selection) =>
                    this.checkPredicates("is_banner_command_available_predicates", selection, "warning") ?? true,
                run: () => {
                    this.insertBanner(_t("Banner Warning"), "⚠️", "warning");
                },
            },
            {
                id: "banner_danger",
                title: _t("Banner Danger"),
                description: _t("Insert a danger banner"),
                icon: "fa-exclamation-circle",
                isAvailable: (selection) =>
                    this.checkPredicates("is_banner_command_available_predicates", selection, "danger") ?? true,
                run: () => {
                    this.insertBanner(_t("Banner Danger"), "❌", "danger");
                },
            },
            {
                id: "banner_monospace",
                title: _t("Monospace"),
                description: _t("Insert a monospace banner"),
                icon: "fa-laptop",
                isAvailable: (selection) =>
                    this.checkPredicates("is_banner_command_available_predicates", selection, "secondary") ?? true,
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
        is_banner_command_available_predicates: (selection, bannerType) => {
            if (
                !isHtmlContentSupported(selection) ||
                closestElement(selection.anchorNode, `.o_editor_banner.alert-${bannerType}`)
            ) {
                return false;
            }
        },
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
        should_show_power_buttons_predicates: ({ anchorNode }) => {
            if (closestElement(anchorNode, ".o_editor_banner")) {
                return false;
            }
        },
        normalize_processors: withSequence(
            5, // before tabs are aligned
            this.handle_monospace_tab_to_spaces.bind(this)
        ),
        move_node_blacklist_selectors: ".o_editor_banner *",
        move_node_whitelist_selectors: ".o_editor_banner",

        /** Overrides */
        delete_backward_overrides: this.handleDeleteBackward.bind(this),
        delete_backward_word_overrides: this.handleDeleteBackward.bind(this),
        shift_tab_overrides: this.handleShiftTab.bind(this),
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

        const bannerClasses = `${containerClass}o_editor_banner user-select-none o-contenteditable-false ${
            emoji ? "lh-1 " : ""
        }d-flex align-items-center alert alert-${alertClass} pb-0 pt-3`;
        const bannerContentClasses = `${contentClass}o_editor_banner_content o-contenteditable-true w-100 px-3`;
        const emojiHtml = emoji
            ? `<i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="${htmlEscape(
                  title
              )}">${htmlEscape(emoji)}</i>`
            : "";
        const selection = this.dependencies.selection.getEditableSelection();
        const currentBanner = closestElement(selection.anchorNode, ".o_editor_banner");
        if (currentBanner) {
            currentBanner.className = bannerClasses;
            const bannerContentEl = currentBanner.querySelector(".o_editor_banner_content");
            bannerContentEl.className = bannerContentClasses;
            const icon = currentBanner.querySelector(".o_editor_banner_icon");
            if (emojiHtml) {
                const newIcon = parseHTML(this.document, emojiHtml).firstChild;
                icon ? icon.replaceWith(newIcon) : currentBanner.prepend(newIcon);
            } else {
                icon.remove();
            }
            this.dependencies.history.addStep();
            return;
        }
        const blockEl = closestBlock(selection.anchorNode);
        let baseContainer;
        if (isParagraphRelatedElement(blockEl)) {
            baseContainer = this.document.createElement(blockEl.nodeName);
            baseContainer.append(...blockEl.childNodes);
        } else if (blockEl.nodeName === "LI") {
            baseContainer = this.dependencies.baseContainer.createBaseContainer({
                children: [...blockEl.childNodes],
            });
            fillShrunkPhrasingParent(blockEl);
        } else {
            baseContainer = this.dependencies.baseContainer.createBaseContainer();
        }
        const baseContainerHtml = baseContainer.outerHTML;
        const bannerElement = parseHTML(
            this.document,
            `<div class="${bannerClasses}" data-oe-role="status">
                ${emojiHtml}
                <div class="${bannerContentClasses}">
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
        bannerElement.replaceWith(baseContainer);
        this.dependencies.selection.setCursorStart(baseContainer);
        return true;
    }

    handle_monospace_tab_to_spaces(root) {
        for (const el of selectElements(root, ".font-monospace.o_editor_banner .oe-tabs")) {
            const spacesElement = document.createTextNode("\u00A0\u00A0\u00A0\u00A0");
            el.replaceWith(spacesElement);
        }
    }

    handleShiftTab() {
        const selection = this.dependencies.selection.getEditableSelection();
        const monospaceBannerElement = closestElement(
            selection.anchorNode,
            ".font-monospace.o_editor_banner"
        );
        if (!monospaceBannerElement) {
            return;
        }
        const fourSpacesRe = /^(?:\u200B*\s\u200B*){4}/;
        for (const block of [...this.dependencies.selection.getTargetedBlocks()]) {
            const text = block.textContent;
            if (text.match(fourSpacesRe)) {
                // Unindent first text node
                const textNode = descendants(block).find(
                    (n) =>
                        n.nodeType === Node.TEXT_NODE &&
                        n.textContent.length &&
                        n.textContent !== "\u200b"
                );
                if (textNode) {
                    textNode.textContent = textNode.textContent.replace(fourSpacesRe, "");
                }
            }
        }
    }
}
