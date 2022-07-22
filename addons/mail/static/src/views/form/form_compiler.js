/** @odoo-module */

import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { SIZES } from "@web/core/ui/ui_service";
import { patch } from "@web/core/utils/patch";
import { append, createElement, setAttributes } from "@web/core/utils/xml";
import { FormCompiler } from "@web/views/form/form_compiler";


function compileChatter(node, params) {
    let hasActivities = false;
    let hasFollowers = false;
    let hasMessageList = false;
    let hasParentReloadOnAttachmentsChanged;
    let hasParentReloadOnFollowersUpdate = false;
    let hasParentReloadOnMessagePosted = false;
    let isAttachmentBoxVisibleInitially = false;
    for (const childNode of node.children) {
        const options = evaluateExpr(childNode.getAttribute("options") || "{}");
        switch (childNode.getAttribute('name')) {
            case 'activity_ids':
                hasActivities = true;
                break;
            case 'message_follower_ids':
                hasFollowers = true;
                hasParentReloadOnFollowersUpdate = Boolean(options['post_refresh']);
                isAttachmentBoxVisibleInitially = isAttachmentBoxVisibleInitially || Boolean(options['open_attachments']);
                break;
            case 'message_ids':
                hasMessageList = true;
                hasParentReloadOnAttachmentsChanged = options['post_refresh'] === 'always';
                hasParentReloadOnMessagePosted = Boolean(options['post_refresh']);
                isAttachmentBoxVisibleInitially = isAttachmentBoxVisibleInitially || Boolean(options['open_attachments']);
                break;
        }
    }
    const chatterContainerXml = createElement("ChatterContainer");
    setAttributes(chatterContainerXml, {
        "hasActivities": hasActivities,
        "hasFollowers": hasFollowers,
        "hasMessageList": hasMessageList,
        "hasParentReloadOnAttachmentsChanged": hasParentReloadOnAttachmentsChanged,
        "hasParentReloadOnFollowersUpdate": hasParentReloadOnFollowersUpdate,
        "hasParentReloadOnMessagePosted": hasParentReloadOnMessagePosted,
        "isAttachmentBoxVisibleInitially": isAttachmentBoxVisibleInitially,
        "threadId": "props.record.resId or undefined",
        "threadModel": "props.record.resModel",
        "webRecord": "props.record",
    });
    const chatterContainerHookXml = createElement("div");
    chatterContainerHookXml.classList.add("o_FormRenderer_chatterContainer");
    append(chatterContainerHookXml, chatterContainerXml);
    return chatterContainerHookXml;
}

function compileAttachmentPreview(node, params) {
    const webClientViewAttachmentViewContainerHookXml = createElement("div");
    webClientViewAttachmentViewContainerHookXml.classList.add('o_attachment_preview');
    const webClientViewAttachmentViewContainerXml = createElement("WebClientViewAttachmentViewContainer");
    setAttributes(webClientViewAttachmentViewContainerXml, {
        "threadId": "props.record.resId or undefined",
        "threadModel": "props.record.resModel",
    });
    append(webClientViewAttachmentViewContainerHookXml, webClientViewAttachmentViewContainerXml);
    return webClientViewAttachmentViewContainerHookXml;
}

registry.category("form_compilers").add("chatter_compiler", {
    selector: "div.oe_chatter",
    fn: compileChatter,
});

registry.category("form_compilers").add("attachment_preview_compiler", {
    selector: "div.o_attachment_preview",
    fn: compileAttachmentPreview,
});

patch(FormCompiler.prototype, 'mail', {
    compile() {
        // TODO no chatter if in dialog?
        const res = this._super(...arguments);
        const chatterContainerHookXml = res.querySelector('.o_FormRenderer_chatterContainer');
        if (!chatterContainerHookXml) {
            return res; // no chatter, keep the result as it is
        }
        const chatterContainerXml = chatterContainerHookXml.querySelector('ChatterContainer');
        if (chatterContainerHookXml.parentNode.classList.contains('o_form_sheet')) {
            setAttributes(chatterContainerXml, {
                "hasExternalBorder": 'true',
                "hasMessageListScrollAdjust": 'false',
            });
            return res; // if chatter is inside sheet, keep it there
        }
        const formSheetBgXml = res.querySelector('.o_form_sheet_bg');
        const parentXml = formSheetBgXml && formSheetBgXml.parentNode;
        if (!parentXml) {
            return res; // miss-config: a sheet-bg is required for the rest
        }
        const webClientViewAttachmentViewHookXml = res.querySelector('.o_attachment_preview');
        // TODO hasAttachmentViewer should also depend on the groups= and/or invisible modifier on o_attachment_preview (see invoice form)
        if (webClientViewAttachmentViewHookXml) {
            // in sheet bg (attachment viewer present)
            setAttributes(webClientViewAttachmentViewHookXml, {
                't-if': `hasAttachmentViewer() and uiService.size >= ${SIZES.XXL}`,
            });
            const sheetBgChatterContainerHookXml = chatterContainerHookXml.cloneNode(true);
            sheetBgChatterContainerHookXml.classList.add('o-isInFormSheetBg');
            setAttributes(sheetBgChatterContainerHookXml, {
                't-if': `hasAttachmentViewer() and uiService.size >= ${SIZES.XXL}`,
            });
            append(formSheetBgXml, sheetBgChatterContainerHookXml);
            const sheetBgChatterContainerXml = sheetBgChatterContainerHookXml.querySelector('ChatterContainer');
            setAttributes(sheetBgChatterContainerXml, {
                "isInFormSheetBg": "true",
                "hasExternalBorder": "true",
                "hasMessageListScrollAdjust": "false",
            });
        }
        // after sheet bg (standard position, either aside or below)
        if (webClientViewAttachmentViewHookXml) {
            setAttributes(chatterContainerHookXml, {
                't-if': `!(hasAttachmentViewer() and uiService.size >= ${SIZES.XXL})`,
                't-attf-class': `{{ uiService.size >= ${SIZES.XXL} and !(hasAttachmentViewer() and uiService.size >= ${SIZES.XXL}) ? "o-aside" : "" }}`,
            });
            setAttributes(chatterContainerXml, {
                "isInFormSheetBg": "hasAttachmentViewer()",
                "hasExternalBorder": `!(uiService.size >= ${SIZES.XXL} and !(hasAttachmentViewer() and uiService.size >= ${SIZES.XXL}))`,
                "hasMessageListScrollAdjust": `uiService.size >= ${SIZES.XXL} and !(hasAttachmentViewer() and uiService.size >= ${SIZES.XXL})`,
            });
        } else {
            setAttributes(chatterContainerXml, {
                "isInFormSheetBg": "false",
                "hasExternalBorder": `uiService.size < ${SIZES.XXL}`,
                "hasMessageListScrollAdjust": `uiService.size >= ${SIZES.XXL}`,
            });
            setAttributes(chatterContainerHookXml, {
                't-attf-class': `{{ uiService.size >= ${SIZES.XXL} ? "o-aside" : "" }}`,
            });
        }
        append(parentXml, chatterContainerHookXml);
        return res;
    },
});
