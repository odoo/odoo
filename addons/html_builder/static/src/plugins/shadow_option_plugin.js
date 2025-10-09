import { BuilderAction } from "@html_builder/core/builder_action";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { parseBoxShadow } from "@html_builder/utils/utils_css";

const shadowClass = "shadow";

export class ShadowOptionPlugin extends Plugin {
    static id = "shadowOption";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_actions: {
            SetShadowClassAction,
            SetShadowModeAction,
            SetShadowStyleAction,
        },
    };
    setup() {
        // Migrate old shadow elements to use the new custom shadow class.
        const oldShadowElements = this.editable.querySelectorAll(".shadow[style*=box-shadow]");
        for (const el of oldShadowElements) {
            el.classList.remove("shadow");
            el.classList.add("o-shadow-custom");
        }
    }
}

export function getDefaultShadow(mode) {
    const el = document.createElement("div");
    el.classList.add(shadowClass);
    document.body.appendChild(el);
    const shadow = `${getComputedStyle(el).boxShadow}${mode === "inset" ? " inset" : ""}`;
    el.remove();
    return shadow;
}

function getShadowMode(editingElement) {
    const currentBoxShadow = getComputedStyle(editingElement)["box-shadow"];
    if (currentBoxShadow === "none") {
        return "none";
    }
    if (currentBoxShadow.includes("inset")) {
        return "inset";
    }
    if (!currentBoxShadow.includes("inset") && currentBoxShadow !== "none") {
        return "outset";
    }
}

function setBoxShadow(editingElement, value) {
    editingElement.style.setProperty("box-shadow", value, "important");
}

export function getCurrentShadow(editingElement) {
    return parseShadow(getComputedStyle(editingElement)["box-shadow"]);
}

function parseShadow(value) {
    if (!value || value === "none") {
        return {};
    }
    return parseBoxShadow(value);
}

export function shadowToString(shadow) {
    if (!shadow) {
        return "";
    }
    return `${shadow.color} ${shadow.offsetX} ${shadow.offsetY} ${shadow.blur} ${shadow.spread} ${
        shadow.mode ? shadow.mode : ""
    }`;
}

registry.category("builder-plugins").add(ShadowOptionPlugin.id, ShadowOptionPlugin);

export class SetShadowClassAction extends ClassAction {
    static id = "setShadowClass";
    apply({ editingElement, params: { mainParam: shadowClass } }) {
        super.apply(...arguments);
        if (shadowClass === "o-shadow-custom" && editingElement.style.boxShadow === "") {
            setBoxShadow(editingElement, getDefaultShadow("shadow"));
        }
    }
    clean({ editingElement, params: { mainParam: shadowClass } }) {
        super.clean(...arguments);
        if (shadowClass === "o-shadow-custom") {
            editingElement.style.removeProperty("box-shadow");
        }
    }
}

export class SetShadowModeAction extends BuilderAction {
    static id = "setShadowMode";
    isApplied({ editingElement, value: shadowMode }) {
        return shadowMode === getShadowMode(editingElement);
    }
    getValue({ editingElement }) {
        return getShadowMode(editingElement, "mode");
    }
    apply({ editingElement, value: shadowMode }) {
        const shadow = getCurrentShadow(editingElement);
        if (shadowMode === "inset") {
            shadow.mode = "inset";
        } else {
            shadow.mode = "";
        }
        setBoxShadow(editingElement, shadowToString(shadow));
    }
}
export class SetShadowStyleAction extends BuilderAction {
    static id = "setShadowStyle";
    apply({ editingElement, params: { mainParam: attributeName }, value }) {
        const shadow = getCurrentShadow(editingElement);
        shadow[attributeName] = value;
        setBoxShadow(editingElement, shadowToString(shadow));
    }
    getValue({ editingElement, params: { mainParam: attributeName } }) {
        return getCurrentShadow(editingElement)[attributeName];
    }
}
