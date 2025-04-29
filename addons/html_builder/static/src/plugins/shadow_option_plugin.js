import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

const shadowClass = "shadow";

class ShadowOptionPlugin extends Plugin {
    static id = "shadowOption";
    static shared = ["getActions"];
    resources = {
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            setShadowMode: {
                isApplied: ({ editingElement, value: shadowMode }) =>
                    shadowMode === getShadowMode(editingElement),
                getValue: ({ editingElement }) => getShadowMode(editingElement, "mode"),
                apply: ({ editingElement, value: shadowMode }) => {
                    if (shadowMode === "none") {
                        editingElement.classList.remove(shadowClass);
                        setBoxShadow(editingElement, "");
                        return;
                    }

                    if (!editingElement.classList.contains(shadowClass)) {
                        editingElement.classList.add(shadowClass);
                    }
                    if (editingElement.style["box-shadow"] === "") {
                        setBoxShadow(editingElement, getDefaultShadow(shadowMode));
                    } else {
                        const shadow = getCurrentShadow(editingElement);
                        if (shadowMode === "inset") {
                            shadow.mode = "inset";
                        } else {
                            shadow.mode = "";
                        }
                        setBoxShadow(editingElement, shadowToString(shadow));
                    }
                },
            },
            setShadow: {
                apply: ({ editingElement, params: { mainParam: attributeName }, value }) => {
                    const shadow = getCurrentShadow(editingElement);
                    shadow[attributeName] = value;
                    setBoxShadow(editingElement, shadowToString(shadow));
                },
                getValue: ({ editingElement, params: { mainParam: attributeName } }) =>
                    getCurrentShadow(editingElement)[attributeName],
            },
        };
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

export function getCurrentShadow(editingElement) {
    return parseShadow(getComputedStyle(editingElement)["box-shadow"]);
}

function parseShadow(value) {
    if (!value || value === "none") {
        return {};
    }
    const regex =
        /(?<color>(rgb(a)?\([^)]*\))|(var\([^)]+\)))\s+(?<offsetX>\d+px)\s+(?<offsetY>\d+px)\s+(?<blur>\d+px)\s+(?<spread>\d+px)(\s+)?(?<mode>\w+)?/;
    return value.match(regex).groups;
}

export function shadowToString(shadow) {
    if (!shadow) {
        return "";
    }
    return `${shadow.color} ${shadow.offsetX} ${shadow.offsetY} ${shadow.blur} ${shadow.spread} ${
        shadow.mode ? shadow.mode : ""
    }`;
}

function setBoxShadow(editingElement, value) {
    editingElement.style.setProperty("box-shadow", value, "important");
}

registry.category("website-plugins").add(ShadowOptionPlugin.id, ShadowOptionPlugin);
