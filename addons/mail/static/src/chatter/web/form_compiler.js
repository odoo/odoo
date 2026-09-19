// @ts-check
/** @odoo-module native */
import { registry } from "@web/core/registry";
import {
    append,
    createElement,
    extractAttributes,
    setAttributes,
} from "@web/core/utils/dom/xml";
import { patch } from "@web/core/utils/patch";
import { FormCompiler } from "@web/views/form";
/**
 * @this {FormCompiler}
 * @param {Element} node
 * @param {Object} params
 * @returns {Element}
 */
function compileChatter(node, params) {
    const chatterContainerXml = createElement("t");
    setAttributes(chatterContainerXml, {
        "t-component": "__comp__.mailComponents.Chatter",
        has_activities: "__comp__.props.archInfo.has_activities",
        hasAttachmentPreview: Boolean(
            this.templates.FormRenderer.querySelector(".o_attachment_preview"),
        ),
        hasParentReloadOnActivityChanged: Boolean(
            node.getAttribute("reload_on_activity"),
        ),
        hasParentReloadOnAttachmentsChanged: Boolean(
            node.getAttribute("reload_on_attachment"),
        ),
        hasParentReloadOnFollowersUpdate: Boolean(
            node.getAttribute("reload_on_follower"),
        ),
        hasParentReloadOnMessagePosted: Boolean(node.getAttribute("reload_on_post")),
        isAttachmentBoxVisibleInitially: Boolean(node.getAttribute("open_attachments")),
        threadId: "__comp__.props.record.resId or undefined",
        threadModel:
            "__comp__.props.archInfo.thread_model or __comp__.props.record.resModel",
        record: "__comp__.props.record",
        highlightMessageId: "__comp__.highlightMessageId",
    });
    const chatterContainerHookXml = createElement("div");
    chatterContainerHookXml.classList.add(
        "o-mail-ChatterContainer",
        "o-mail-Form-chatter",
    );
    setAttributes(chatterContainerHookXml, { "t-if": "!__comp__.env.inDialog" });
    append(chatterContainerHookXml, chatterContainerXml);
    return chatterContainerHookXml;
}

/**
 * @param {Element} node
 * @param {Object} params
 * @returns {Element}
 */
function compileAttachmentPreview(node, params) {
    const webClientViewAttachmentViewContainerHookXml = createElement("div");
    webClientViewAttachmentViewContainerHookXml.classList.add("o_attachment_preview");
    const webClientViewAttachmentViewContainerXml = createElement("t");
    setAttributes(webClientViewAttachmentViewContainerXml, {
        "t-component": "__comp__.mailComponents.AttachmentView",
        threadId: "__comp__.props.record.resId or undefined",
        threadModel:
            "__comp__.props.archInfo.thread_model or __comp__.props.record.resModel",
    });
    append(
        webClientViewAttachmentViewContainerHookXml,
        webClientViewAttachmentViewContainerXml,
    );
    return webClientViewAttachmentViewContainerHookXml;
}

registry.category("form_compilers").add("chatter_compiler", {
    selector: "chatter",
    fn: compileChatter,
});

registry.category("form_compilers").add("attachment_preview_compiler", {
    selector: "div.o_attachment_preview",
    fn: compileAttachmentPreview,
});

patch(FormCompiler.prototype, {
    /**
     * @param {Element} node
     * @param {Object} params
     * @returns {Element}
     */
    compile(node, params) {
        const res = super.compile(node, params);
        const chatterContainerHookXml = res.querySelector(".o-mail-Form-chatter");
        if (!chatterContainerHookXml) {
            return res;
        }
        const chatterContainerXml = chatterContainerHookXml.querySelector(
            "t[t-component='__comp__.mailComponents.Chatter']",
        );
        setAttributes(chatterContainerXml, {
            isChatterAside: "false",
            isInFormSheetBg: "false",
            saveRecord: "__comp__.props.saveRecord",
        });
        if (chatterContainerHookXml.parentNode.classList.contains("o_form_sheet")) {
            return res;
        }
        const formSheetBgXml = res.querySelector(".o_form_sheet_bg");
        const parentXml = formSheetBgXml && formSheetBgXml.parentNode;
        if (!parentXml) {
            return res;
        }

        const webClientViewAttachmentViewHookXml = res.querySelector(
            ".o_attachment_preview",
        );
        const hasPreview = !!webClientViewAttachmentViewHookXml;
        if (webClientViewAttachmentViewHookXml) {
            setAttributes(webClientViewAttachmentViewHookXml, {
                "t-if": `__comp__.mailLayout(${hasPreview}).includes("COMBO")`,
            });
            const sheetBgChatterContainerHookXml =
                chatterContainerHookXml.cloneNode(true);
            sheetBgChatterContainerHookXml.classList.add("o-isInFormSheetBg", "w-auto");
            setAttributes(sheetBgChatterContainerHookXml, {
                "t-if": `__comp__.mailLayout(${hasPreview}) == "COMBO"`,
            });
            append(formSheetBgXml, sheetBgChatterContainerHookXml);
            const sheetBgChatterContainerXml =
                sheetBgChatterContainerHookXml.querySelector(
                    "t[t-component='__comp__.mailComponents.Chatter']",
                );
            setAttributes(sheetBgChatterContainerXml, {
                isInFormSheetBg: "true",
                isChatterAside: "false",
            });
        }
        setAttributes(chatterContainerXml, {
            isInFormSheetBg: `["COMBO", "BOTTOM_CHATTER"].includes(__comp__.mailLayout(${hasPreview}))`,
            isChatterAside: `["SIDE_CHATTER", "EXTERNAL_COMBO_XXL", "EXTERNAL_COMBO"].includes(__comp__.mailLayout(${hasPreview}))`,
        });
        const { ["t-if"]: tIf } = extractAttributes(chatterContainerHookXml, ["t-if"]);
        setAttributes(chatterContainerHookXml, {
            "t-if": `${
                tIf ? tIf : "true"
            } and (!["COMBO", "NONE"].includes(__comp__.mailLayout(${hasPreview})))`,
            "t-attf-class": `{{ ["SIDE_CHATTER", "EXTERNAL_COMBO_XXL"].includes(__comp__.mailLayout(${hasPreview})) ? "o-aside w-print-100" : "mt-4 mt-md-0" }}`,
        });
        append(parentXml, chatterContainerHookXml);
        return res;
    },
});
