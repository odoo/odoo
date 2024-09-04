import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

function isAvailable(node) {
    return !!closestElement(node, ".o_editor_banner");
}
export class BannerPlugin extends Plugin {
    static name = "banner";
    static dependencies = ["dom", "emoji", "selection"];
    resources = {
        powerboxCategory: withSequence(20, { id: "banner", name: _t("Banner") }),
        powerboxItems: [
            {
                category: "banner",
                name: _t("Banner Info"),
                description: _t("Insert an info banner"),
                fontawesome: "fa-info-circle",
                isAvailable,
                action: () => {
                    this.insertBanner(_t("Banner Info"), "💡", "info");
                },
            },
            {
                category: "banner",
                name: _t("Banner Success"),
                description: _t("Insert an success banner"),
                fontawesome: "fa-check-circle",
                isAvailable,
                action: () => {
                    this.insertBanner(_t("Banner Success"), "✅", "success");
                },
            },
            {
                category: "banner",
                name: _t("Banner Warning"),
                description: _t("Insert an warning banner"),
                fontawesome: "fa-exclamation-triangle",
                isAvailable,
                action: () => {
                    this.insertBanner(_t("Banner Warning"), "⚠️", "warning");
                },
            },
            {
                category: "banner",
                name: _t("Banner Danger"),
                description: _t("Insert an danger banner"),
                fontawesome: "fa-exclamation-circle",
                isAvailable,
                action: () => {
                    this.insertBanner(_t("Banner Danger"), "❌", "danger");
                },
            },
        ],
        showPowerButtons: (selection) => !closestElement(selection.anchorNode, ".o_editor_banner"),
    };

    setup() {
        this.addDomListener(this.editable, "click", (e) => {
            if (e.target.classList.contains("o_editor_banner_icon")) {
                this.onBannerEmojiChange(e.target);
            }
        });
    }

    insertBanner(title, emoji, alertClass) {
        const bannerElement = parseHTML(
            this.document,
            `<div class="o_editor_banner user-select-none o_not_editable lh-1 d-flex align-items-center alert alert-${alertClass} pb-0 pt-3" role="status" contenteditable="false">
                <i class="o_editor_banner_icon mb-3 fst-normal" aria-label="${title}">${emoji}</i>
                <div class="w-100 px-3" contenteditable="true">
                    <p><br></p>
                </div>
            </div`
        ).childNodes[0];
        this.shared.domInsert(bannerElement);
        // If the first child of editable is contenteditable false element
        // a chromium bug prevents selecting the container. Prepend a
        // zero-width space so it's no longer the first child.
        if (this.editable.firstChild === bannerElement) {
            const zws = document.createTextNode("\u200B");
            bannerElement.before(zws);
        }
        this.shared.setCursorStart(bannerElement.querySelector(".o_editor_banner > div > p"));
        this.dispatch("ADD_STEP");
    }

    onBannerEmojiChange(iconElement) {
        this.shared.showEmojiPicker({
            target: iconElement,
            onSelect: (emoji) => {
                iconElement.textContent = emoji;
                this.dispatch("ADD_STEP");
            },
        });
    }
}
