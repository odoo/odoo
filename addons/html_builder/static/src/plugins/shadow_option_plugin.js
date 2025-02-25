import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

const shadowClass = "shadow";

class ShadowOptionPlugin extends Plugin {
    static id = "shadowOption";
    resources = {
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            setShadowMode: {
                isApplied: ({ editingElement, param: shadowMode }) => {
                    const currentBoxShadow = editingElement.style["box-shadow"];
                    if (shadowMode === "none") {
                        return currentBoxShadow === "";
                    }
                    if (shadowMode === "inset") {
                        return currentBoxShadow.includes("inset");
                    }
                    if (shadowMode === "outset") {
                        return !currentBoxShadow.includes("inset") && currentBoxShadow !== "";
                    }
                },
                apply: ({ editingElement, param: shadowMode }) => {
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
                apply: ({ editingElement, param, value }) => {
                    const shadow = getCurrentShadow(editingElement);
                    shadow[param] = value;
                    setBoxShadow(editingElement, shadowToString(shadow));
                },
                getValue: ({ editingElement, param }) => getCurrentShadow(editingElement)[param],
            },
        };
    }
}

function getDefaultShadow(mode) {
    const el = document.createElement("div");
    el.classList.add(shadowClass);
    document.body.appendChild(el);
    const shadow = `${getComputedStyle(el).boxShadow}${mode === "inset" ? " inset" : ""}`;
    el.remove();
    return shadow;
}

function getCurrentShadow(editingElement) {
    return parseShadow(editingElement.style["box-shadow"]);
}

function parseShadow(value) {
    if (!value) {
        return {};
    }
    const regex =
        /(?<color>(rgb(a)?\([^)]*\))|(var\([^)]+\)))\s+(?<offsetX>\d+px)\s+(?<offsetY>\d+px)\s+(?<blur>\d+px)\s+(?<spread>\d+px)(\s+)?(?<mode>\w+)?/;
    return value.match(regex).groups;
}

function shadowToString(shadow) {
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
