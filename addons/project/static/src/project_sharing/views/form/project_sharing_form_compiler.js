import { append, createElement, setAttributes } from "@web/core/utils/xml";
import { registry } from "@web/core/registry";
import { SIZES } from "@web/core/ui/ui_service";
import { patch } from "@web/core/utils/patch";
import { FormCompiler } from "@web/views/form/form_compiler";

/**
 * Compiler the portal chatter in project sharing.
 *
 * @param {HTMLElement} node
 * @param {Object} params
 * @returns
 */
function compileChatter(node, params) {
    const chatterContainerXml = createElement("Chatter");
    const parentURLQuery = new URLSearchParams(window.parent.location.search);
    setAttributes(chatterContainerXml, {
        token: `'${parentURLQuery.get("access_token")}'` || "",
        threadModel: params.resModel,
        threadId: params.resId,
        projectSharingId: params.projectSharingId,
        isFollower: params.isFollower,
        displayFollowButton: params.displayFollowButton,
    });
    const chatterContainerHookXml = createElement("div");
    chatterContainerHookXml.classList.add("o-mail-ChatterContainer", "o-mail-Form-chatter", "pt-2");
    append(chatterContainerHookXml, chatterContainerXml);
    return chatterContainerHookXml;
}

registry.category("form_compilers").add("portal_chatter_compiler", {
    selector: "chatter",
    fn: (node) =>
        compileChatter(node, {
            resId: "__comp__.props.record.resId or undefined",
            resModel: "__comp__.props.record.resModel",
            projectSharingId: "__comp__.props.record.context.active_id_chatter",
            isFollower: "__comp__.props.record.data.message_is_follower",
            displayFollowButton: "__comp__.props.record.data.display_follow_button",
        }),
});

patch(FormCompiler.prototype, {
    compile(node, params) {
        const res = super.compile(node, params);
        const chatterContainerHookXml = res.querySelector(".o-mail-Form-chatter");
        if (!chatterContainerHookXml) {
            return res; // no chatter, keep the result as it is
        }
        if (chatterContainerHookXml.parentNode.classList.contains("o_form_sheet")) {
            return res; // if chatter is inside sheet, keep it there
        }
        const formSheetBgXml = res.querySelector(".o_form_sheet_bg");
        const parentXml = formSheetBgXml && formSheetBgXml.parentNode;
        if (!parentXml) {
            return res; // miss-config: a sheet-bg is required for the rest
        }
        // after sheet bg (standard position, below form)
        setAttributes(chatterContainerHookXml, {
            "t-att-class": `{
                "overflow-x-hidden overflow-y-auto o-aside h-100": __comp__.uiService.size >= ${SIZES.XXL},
                "px-3 py-0": __comp__.uiService.size < ${SIZES.XXL},
            }`,
        });
        append(parentXml, chatterContainerHookXml);
        return res;
    },
});
