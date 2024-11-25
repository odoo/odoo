import { _t } from "@web/core/l10n/translation";
const oeStructureSelector = "#wrapwrap .oe_structure[data-oe-xpath][data-oe-id]";
const oeFieldSelector = "#wrapwrap [data-oe-field]:not([data-oe-sanitize-prevent-edition])";
export const OE_RECORD_COVER_SELECTOR = "#wrapwrap .o_record_cover_container[data-res-model]";
const oeCoverSelector = `#wrapwrap .s_cover[data-res-model], ${OE_RECORD_COVER_SELECTOR}`;
export const SAVABLE_SELECTOR = `${oeStructureSelector}, ${oeFieldSelector}, ${oeCoverSelector}`;

export function getSnippetName(snippetEl) {
    if (snippetEl.dataset["name"] !== undefined) {
        return snippetEl.dataset["name"];
    }
    if (snippetEl.tagName === "IMG") {
        return _t("Image");
    }
    if (snippetEl.classList.contains("fa")) {
        return _t("Icon");
    }
    if (snippetEl.classList.contains(".media_iframe_video")) {
        return _t("Video");
    }
    if (snippetEl.parentElement && snippetEl.parentElement.classList.contains("row")) {
        return _t("Column");
    }
    if (snippetEl.matches("#wrapwrap .s_popup")) {
        return _t("Page Options");
    }
    if (snippetEl.classList.contains("btn")) {
        return _t("Button");
    }
    return _t("Block");
}
