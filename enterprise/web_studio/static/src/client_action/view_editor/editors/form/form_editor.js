import { formView } from "@web/views/form/form_view";
import { FormEditorRenderer } from "./form_editor_renderer/form_editor_renderer";
import { FormEditorController } from "./form_editor_controller/form_editor_controller";
import { FormEditorCompiler } from "./form_editor_compiler";
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";
import {
    makeModelErrorResilient,
    randomName,
} from "@web_studio/client_action/view_editor/editors/utils";
import { getModifier } from "@web/views/view_compiler";
import { FormEditorSidebar } from "./form_editor_sidebar/form_editor_sidebar";
import { getStudioNoFetchFields } from "../utils";

class EditorArchParser extends formView.ArchParser {
    parse() {
        const archInfo = super.parse(...arguments);
        this.omitStudioNoFetchFields(archInfo);
        return archInfo;
    }

    omitStudioNoFetchFields(archInfo) {
        const noFetch = getStudioNoFetchFields(archInfo.fieldNodes);
        archInfo.fieldNodes = omit(archInfo.fieldNodes, ...noFetch.fieldNodes);

        for (const fieldNode of Object.values(archInfo.fieldNodes)) {
            if (fieldNode.views) {
                for (const fieldArchInfo of Object.values(fieldNode.views)) {
                    this.omitStudioNoFetchFields(fieldArchInfo);
                }
            }
        }
    }
}

class Model extends formView.Model {}
Model.Record = class RecordNoEdit extends formView.Model.Record {
    get isInEdition() {
        return false;
    }
    _save() {
        return true
    }
};

export const formEditor = {
    ...formView,
    ArchParser: EditorArchParser,
    Compiler: FormEditorCompiler,
    Renderer: FormEditorRenderer,
    Controller: FormEditorController,
    props(genericProps, editor, config) {
        const arch = genericProps.arch;
        Array.from(arch.querySelectorAll("field > list, field > form, field > kanban")).forEach(
            (el) => {
                // Inline subviews sometimes have a "groups" attribute, allowing to have different
                // x2many views depending on access rights. Outside Studio, this has no impact
                // client side, because the view processing in python would remove nodes with groups
                // the user doesn't belong to. However, when there's a "studio" key in the context,
                // nodes are no longer removed but they are set as invisible="1" instead. This means
                // that in Studio, we can have several x2many subviews for the same view type (even
                // tough, only one of them should be visible). Here, we're only interested in the
                // views that are visible (the ones the user has access to), so we remove the others.
                if (getModifier(el, "invisible")) {
                    el.remove();
                }
            }
        );
        const props = formView.props(genericProps, editor, config);
        props.Model = makeModelErrorResilient(Model);
        props.preventEdit = true;
        return props;
    },
    Sidebar: FormEditorSidebar,
};
registry.category("studio_editors").add("form", formEditor);

/**
 *  Drag/Drop Validation
 */
const HOOK_CLASS_WHITELIST = [
    "o_web_studio_field_signature",
    "o_web_studio_field_html",
    "o_web_studio_field_many2many",
    "o_web_studio_field_one2many",
    "o_web_studio_field_tabs",
    "o_web_studio_field_columns",
    "o_web_studio_field_lines",
];
const HOOK_TYPE_BLACKLIST = ["genericTag", "afterGroup", "afterNotebook", "insideSheet"];

const isBlackListedHook = (draggedEl, hookEl) =>
    !HOOK_CLASS_WHITELIST.some((cls) => draggedEl.classList.contains(cls)) &&
    HOOK_TYPE_BLACKLIST.some((t) => hookEl.dataset.type === t);

function canDropNotebook(hookEl) {
    if (hookEl.dataset.type === "page") {
        return false;
    }
    if (hookEl.closest(".o_group") || hookEl.closest(".o_inner_group")) {
        return false;
    }
    return true;
}

function canDropGroup(hookEl) {
    if (hookEl.dataset.type === "insideGroup") {
        return false;
    }
    if (hookEl.closest(".o_group") || hookEl.closest(".o_inner_group")) {
        return false;
    }
    return true;
}

function isValidFormHook({ hook, element }) {
    const draggingStructure = element.dataset.structure;
    switch (draggingStructure) {
        case "notebook": {
            if (!canDropNotebook(hook)) {
                return false;
            }
            break;
        }
        case "group": {
            if (!canDropGroup(hook)) {
                return false;
            }
            break;
        }
    }
    if (isBlackListedHook(element, hook)) {
        return false;
    }

    return true;
}
formEditor.isValidHook = isValidFormHook;

function addFormViewStructure(structure) {
    switch (structure) {
        case "notebook":
        case "group": {
            return {
                node: {
                    tag: structure,
                    attrs: {
                        name: randomName(`studio_${structure}`),
                    },
                },
            };
        }
    }
}
formEditor.addViewStructure = addFormViewStructure;
