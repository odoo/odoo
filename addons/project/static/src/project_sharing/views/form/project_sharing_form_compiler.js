/** @odoo-module */

import { append, createElement, setAttributes } from "@web/core/utils/xml";
import { registry } from "@web/core/registry";
import { SIZES } from "@web/core/ui/ui_service";
import { getModifier, ViewCompiler } from "@web/views/view_compiler";
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
    const chatterContainerXml = createElement('ChatterContainer');
    const parentURLQuery = new URLSearchParams(window.parent.location.search);
    setAttributes(chatterContainerXml, {
        token: `'${parentURLQuery.get('access_token')}'` || '',
        resModel: params.resModel,
        resId: params.resId,
        projectSharingId: params.projectSharingId,
    });
    const chatterContainerHookXml = createElement('div');
    chatterContainerHookXml.classList.add('o-mail-Form-chatter');
    append(chatterContainerHookXml, chatterContainerXml);
    return chatterContainerHookXml;
}

export class ProjectSharingChatterCompiler extends ViewCompiler {
    setup() {
        this.compilers.push({ selector: "t", fn: this.compileT });
        this.compilers.push({ selector: 'div.oe_chatter', fn: this.compileChatter });
    }

    compile(node, params) {
        const res = super.compile(node, params).children[0];
        const chatterContainerHookXml = res.querySelector(".o-mail-Form-chatter");
        if (chatterContainerHookXml) {
            setAttributes(chatterContainerHookXml, {
                "t-if": `__comp__.uiService.size >= ${SIZES.XXL}`,
            });
            chatterContainerHookXml.classList.add('overflow-x-hidden', 'overflow-y-auto', 'o-aside', 'h-100', 'd-none');
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
                recordExpr: "__comp__.model.root",
            });
            append(compiledRoot, compiledChild);
        }
        return compiledRoot;
    }

    compileChatter(node) {
        return compileChatter(node, {
            resId: '__comp__.model.root.resId or undefined',
            resModel: '__comp__.model.root.resModel',
            projectSharingId: '__comp__.model.root.context.active_id_chatter',
        });
    }
}

registry.category("form_compilers").add("portal_chatter_compiler", {
    selector: "div.oe_chatter",
    fn: (node) =>
        compileChatter(node, {
            resId: "__comp__.props.record.resId or undefined",
            resModel: "__comp__.props.record.resModel",
            projectSharingId: "__comp__.props.record.context.active_id_chatter",
        }),
});

patch(FormCompiler.prototype, {
    compile(node, params) {
        const res = super.compile(node, params);
        const chatterContainerHookXml = res.querySelector('.o-mail-Form-chatter');
        if (!chatterContainerHookXml) {
            return res; // no chatter, keep the result as it is
        }
        if (chatterContainerHookXml.parentNode.classList.contains('o_form_sheet')) {
            return res; // if chatter is inside sheet, keep it there
        }
        const formSheetBgXml = res.querySelector('.o_form_sheet_bg');
        const parentXml = formSheetBgXml && formSheetBgXml.parentNode;
        if (!parentXml) {
            return res; // miss-config: a sheet-bg is required for the rest
        }
        // after sheet bg (standard position, below form)
        setAttributes(chatterContainerHookXml, {
            't-att-class': `{
                'overflow-x-hidden overflow-y-auto o-aside h-100': __comp__.uiService.size >= ${SIZES.XXL},
                'px-3 py-0': __comp__.uiService.size < ${SIZES.XXL},
            }`,
        });
        append(parentXml, chatterContainerHookXml);
        return res;
    }
});
