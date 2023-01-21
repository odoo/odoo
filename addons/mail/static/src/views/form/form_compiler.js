/** @odoo-module */

import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { SIZES } from "@web/core/ui/ui_service";
import { patch } from "@web/core/utils/patch";
import { append, createElement, setAttributes } from "@web/core/utils/xml";
import { ViewCompiler, getModifier } from "@web/views/view_compiler";
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
        "chatter": params.chatter,
        "hasActivities": hasActivities,
        "hasFollowers": hasFollowers,
        "hasMessageList": hasMessageList,
        "hasParentReloadOnAttachmentsChanged": hasParentReloadOnAttachmentsChanged,
        "hasParentReloadOnFollowersUpdate": hasParentReloadOnFollowersUpdate,
        "hasParentReloadOnMessagePosted": hasParentReloadOnMessagePosted,
        "isAttachmentBoxVisibleInitially": isAttachmentBoxVisibleInitially,
        "threadId": params.threadId,
        "threadModel": params.threadModel,
        "webRecord": params.webRecord,
        "saveRecord": "() => this.saveButtonClicked and this.saveButtonClicked()",
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
        "threadId": params.threadId,
        "threadModel": params.threadModel,
    });
    append(webClientViewAttachmentViewContainerHookXml, webClientViewAttachmentViewContainerXml);
    return webClientViewAttachmentViewContainerHookXml;
}

export class MailFormCompiler extends ViewCompiler {
    setup() {
        this.compilers.push({ selector: "t", fn: this.compileT });
        this.compilers.push({ selector: "div.oe_chatter", fn: this.compileChatter });
        this.compilers.push({
            selector: "div.o_attachment_preview",
            fn: this.compileAttachmentPreview,
        });
    }

    compile(node, params) {
        const res = super.compile(node, params).children[0];
        const chatterContainerHookXml = res.querySelector(".o_FormRenderer_chatterContainer");
        if (chatterContainerHookXml) {
            setAttributes(chatterContainerHookXml, {
                "t-if": `!hasAttachmentViewer() and uiService.size >= ${SIZES.XXL}`,
                "t-attf-class": "o-aside",
            });
            const chatterContainerXml = chatterContainerHookXml.querySelector('ChatterContainer');
            setAttributes(chatterContainerXml, {
                "hasExternalBorder": "false",
                "hasMessageListScrollAdjust": "true",
                "isInFormSheetBg": "false",
            });
        }
        const attachmentViewHookXml = res.querySelector(".o_attachment_preview");
        if (attachmentViewHookXml) {
            setAttributes(attachmentViewHookXml, {
                "t-if": `hasAttachmentViewer()`,
            });
        }
        return res;
    }

    compileT(node, params) {
        const compiledRoot = createElement("t");
        for (const child of node.childNodes) {
            const invisible = getModifier(child, "invisible");
            let compiledChild = this.compileNode(child, params, false);
            compiledChild = this.applyInvisible(invisible, compiledChild, {
                ...params,
                recordExpr: "model.root",
            });
            append(compiledRoot, compiledChild);
        }
        return compiledRoot;
    }

    compileChatter(node) {
        return compileChatter(node, {
            chatter: "chatter",
            threadId: "model.root.resId or undefined",
            threadModel: "model.root.resModel",
            webRecord: "model.root",
        });
    }

    compileAttachmentPreview(node) {
        return compileAttachmentPreview(node, {
            threadId: "model.root.resId or undefined",
            threadModel: "model.root.resModel",
        });
    }
}

registry.category("form_compilers").add("chatter_compiler", {
    selector: "div.oe_chatter",
    fn: (node) =>
        compileChatter(node, {
            chatter: "props.chatter",
            threadId: "props.record.resId or undefined",
            threadModel: "props.record.resModel",
            webRecord: "props.record",
        }),
});

registry.category("form_compilers").add("attachment_preview_compiler", {
    selector: "div.o_attachment_preview",
    fn: (node) =>
        compileAttachmentPreview(node, {
            threadId: "props.record.resId or undefined",
            threadModel: "props.record.resModel",
        }),
});

patch(FormCompiler.prototype, 'mail', {
    compile(node, params) {
        // TODO no chatter if in dialog?
        const res = this._super(node, params);
        const chatterContainerHookXml = res.querySelector('.o_FormRenderer_chatterContainer');
        if (!chatterContainerHookXml) {
            return res; // no chatter, keep the result as it is
        }
        const chatterContainerXml = chatterContainerHookXml.querySelector('ChatterContainer');
        setAttributes(chatterContainerXml, {
            "hasExternalBorder": "true",
            "hasMessageListScrollAdjust": "false",
            "isInFormSheetBg": "false",
            "saveRecord": "this.props.saveButtonClicked",
        });
        if (chatterContainerHookXml.parentNode.classList.contains('o_form_sheet')) {
            return res; // if chatter is inside sheet, keep it there
        }
        const formSheetBgXml = res.querySelector('.o_form_sheet_bg');
        const parentXml = formSheetBgXml && formSheetBgXml.parentNode;
        if (!parentXml) {
            return res; // miss-config: a sheet-bg is required for the rest
        }
        if (params.hasAttachmentViewerInArch) {
            // in sheet bg (attachment viewer present)
            const sheetBgChatterContainerHookXml = chatterContainerHookXml.cloneNode(true);
            sheetBgChatterContainerHookXml.classList.add('o-isInFormSheetBg');
            setAttributes(sheetBgChatterContainerHookXml, {
                't-if': `this.props.hasAttachmentViewer`,
            });
            append(formSheetBgXml, sheetBgChatterContainerHookXml);
            const sheetBgChatterContainerXml = sheetBgChatterContainerHookXml.querySelector('ChatterContainer');
            setAttributes(sheetBgChatterContainerXml, {
                "isInFormSheetBg": "true",
            });
        }
        // after sheet bg (standard position, below form)
        setAttributes(chatterContainerHookXml, {
            't-if': `!this.props.hasAttachmentViewer and uiService.size < ${SIZES.XXL}`,
        });
        append(parentXml, chatterContainerHookXml);
        return res;
    },
});
