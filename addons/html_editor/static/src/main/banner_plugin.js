import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { parseHTML } from "@html_editor/utils/html";
import { _t } from "@web/core/l10n/translation";

function isDisabled(node) {
    return !!closestElement(node, ".o_editor_banner");
}
export class BannerPlugin extends Plugin {
    static name = "banner";
    static dependencies = ["dom", "selection"];
    /** @type { (p: BannerPlugin) => Record<string, any> } */
    static resources = (p) => ({
        powerboxCategory: { id: "banner", name: _t("Banner"), sequence: 65 },
        powerboxCommands: [
            {
                category: "banner",
                name: _t("Banner Info"),
                description: _t("Insert an info banner"),
                fontawesome: "fa-info-circle",
                isDisabled,
                action() {
                    p.insertBanner(_t("Banner Info"), "💡", "info");
                },
            },
            {
                category: "banner",
                name: _t("Banner Success"),
                description: _t("Insert an success banner"),
                fontawesome: "fa-check-circle",
                isDisabled,
                action() {
                    p.insertBanner(_t("Banner Success"), "✅", "success");
                },
            },
            {
                category: "banner",
                name: _t("Banner Warning"),
                description: _t("Insert an warning banner"),
                fontawesome: "fa-exclamation-triangle",
                isDisabled,
                action() {
                    p.insertBanner(_t("Banner Warning"), "⚠️", "warning");
                },
            },
            {
                category: "banner",
                name: _t("Banner Danger"),
                description: _t("Insert an danger banner"),
                fontawesome: "fa-exclamation-circle",
                isDisabled,
                action() {
                    p.insertBanner(_t("Banner Danger"), "❌", "danger");
                },
            },
        ],
    });

    insertBanner(title, emoji, alertClass) {
        const bannerElement = parseHTML(
            this.document,
            `<div class="o_editor_banner o_not_editable lh-1 d-flex align-items-center alert alert-${alertClass} pb-0 pt-3" role="status" contenteditable="false">
                <i class="o_editor_banner_icon mb-3 fst-normal" aria-label="${title}">${emoji}</i>
                <div class="w-100 ms-3" contenteditable="true">
                    <p><br></p>
                </div>
            </div`
        ).childNodes[0];
        this.shared.domInsert(bannerElement);
        this.shared.setCursorStart(bannerElement.querySelector(".o_editor_banner > div > p"));
        this.dispatch("ADD_STEP");
    }
}
