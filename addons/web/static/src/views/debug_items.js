/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { editModelDebug } from "@web/core/debug/debug_utils";
import { registry } from "@web/core/registry";

const { tags } = owl;

const debugRegistry = registry.category("debug");

class FieldViewGetDialog extends Dialog {}
FieldViewGetDialog.props = Object.assign({}, Dialog.props, {
    arch: { type: String },
    close: Function,
});
FieldViewGetDialog.bodyTemplate = tags.xml`<pre t-esc="props.arch"/>`;
FieldViewGetDialog.title = _lt("Fields View Get");

function viewSeparator() {
    return {
        type: "separator",
        sequence: 300,
    };
}

function fieldsViewGet({ component, env }) {
    let { arch } = component.props;
    if ("viewInfo" in component.props) {
        //legacy
        arch = component.props.viewInfo.arch;
    }
    return {
        type: "item",
        description: env._t("Fields View Get"),
        callback: () => {
            env.services.dialog.add(FieldViewGetDialog, { arch });
        },
        sequence: 340,
    };
}

export function editView({ accessRights, component, env }) {
    if (!accessRights.canEditView) {
        return null;
    }
    let { viewId, viewType: type } = component.env.config || {}; // fallback is there for legacy
    if ("viewInfo" in component.props) {
        // legacy
        viewId = component.props.viewInfo.view_id;
        type = component.props.viewInfo.type;
        type = type === "tree" ? "list" : type;
    }
    const displayName = type[0].toUpperCase() + type.slice(1);
    const description = env._t("Edit View: ") + displayName;
    return {
        type: "item",
        description,
        callback: () => {
            editModelDebug(env, description, "ir.ui.view", viewId);
        },
        sequence: 350,
    };
}

export function editSearchView({ accessRights, component, env }) {
    if (!accessRights.canEditView) {
        return null;
    }
    let { searchViewId } = component.props.info || {}; // fallback is there for legacy
    if ("viewParams" in component.props) {
        //legacy
        if (!component.props.viewParams.action.controlPanelFieldsView) {
            return null;
        }
        searchViewId = component.props.viewParams.action.controlPanelFieldsView.view_id;
    }
    if (searchViewId === undefined) {
        return null;
    }
    const description = env._t("Edit ControlPanelView");
    return {
        type: "item",
        description,
        callback: () => {
            editModelDebug(env, description, "ir.ui.view", searchViewId);
        },
        sequence: 360,
    };
}

debugRegistry
    .category("view")
    .add("viewSeparator", viewSeparator)
    .add("fieldsViewGet", fieldsViewGet)
    .add("editView", editView)
    .add("editSearchView", editSearchView);
