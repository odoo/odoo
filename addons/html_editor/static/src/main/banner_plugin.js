import { Plugin } from "@html_editor/plugin";
import { fillShrunkPhrasingParent } from "@html_editor/utils/dom";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { withSequence } from "@html_editor/utils/resource";
import { htmlEscape } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

function isAvailable(selection) {
    return !closestElement(selection.anchorNode, ".o_editor_banner");
}
export class BannerPlugin extends Plugin {
    static id = "banner";
    // sanitize plugin is required to handle `contenteditable` attribute.
    static dependencies = ["baseContainer", "history", "dom", "emoji", "selection", "sanitize"];
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
        ],
        power_buttons_visibility_predicates: ({ anchorNode }) =>
            !closestElement(anchorNode, ".o_editor_banner"),
    };

    setup() {
        this.addDomListener(this.editable, "click", (e) => {
            if (e.target.classList.contains("o_editor_banner_icon")) {
                this.onBannerEmojiChange(e.target);
            }
        });
    }

    insertBanner(title, emoji, alertClass) {
        const baseContainer = this.dependencies.baseContainer.createBaseContainer();
        fillShrunkPhrasingParent(baseContainer);
        const baseContainerHtml = baseContainer.outerHTML;
        const bannerElement = parseHTML(
            this.document,
            `<div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-${alertClass} pb-0 pt-3" data-oe-role="status">
                <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="${htmlEscape(
                    title
                )}">${emoji}</i>
                <div class="o_editor_banner_content o-contenteditable-true w-100 px-3">
                    ${baseContainerHtml}
                </div>
            </div`
        ).childNodes[0];
        this.dependencies.dom.insert(bannerElement);
        // If the first child of editable is contenteditable false element
        // a chromium bug prevents selecting the container.
        // Add a baseContainer above it so it's no longer the first child.
        if (this.editable.firstChild === bannerElement) {
            const baseContainer = this.dependencies.baseContainer.createBaseContainer();
            baseContainer.append(this.document.createElement("br"));
            bannerElement.before(baseContainer);
        }
        const baseContainerName = this.dependencies.baseContainer.getDefaultNodeName();
        this.dependencies.selection.setCursorStart(
            bannerElement.querySelector(`.o_editor_banner_content > ${baseContainerName}`)
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
}
