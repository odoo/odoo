import {append, createElement, setAttributes} from "@web/core/utils/xml";
import {FormCompiler} from "@web/views/form/form_compiler";
import {patch} from "@web/core/utils/patch";

patch(FormCompiler.prototype, {
    compile(node, params) {
        const res = super.compile(node, params);
        const formSheetBgXml = res.querySelector(".o_form_sheet_bg");
        const parentXml = formSheetBgXml && formSheetBgXml.parentNode;
        if (!parentXml) {
            return res;
        }
        const AttachmentPreviewWidgetContainerXml = createElement("t");
        setAttributes(AttachmentPreviewWidgetContainerXml, {
            "t-component": "__comp__.mailComponents.AttachmentPreviewWidget",
        });
        append(parentXml, AttachmentPreviewWidgetContainerXml);
        return res;
    },
});
