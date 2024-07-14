/** @odoo-module */
import { sortBy } from "@web/core/utils/arrays";
import { registry } from "@web/core/registry";
import { SIDEBAR_SAFE_FIELDS } from "@web_studio/client_action/view_editor/editors/sidebar_safe_fields";
import { useComponent, useEffect, useRef } from "@odoo/owl";

export const hookPositionTolerance = 50;

export function cleanHooks(el) {
    for (const hookEl of el.querySelectorAll(".o_web_studio_nearest_hook")) {
        hookEl.classList.remove("o_web_studio_nearest_hook");
    }
}

export function getActiveHook(el) {
    return el.querySelector(".o_web_studio_nearest_hook");
}

// A naive function that determines if the toXpath on which we dropped
// our object is actually the same as the fromXpath of the element we dropped.
// Naive because it won't evaluate xpath, just guess whether they are equivalent
// under precise conditions.
export function isToXpathEquivalentFromXpath(position, toXpath, fromXpath) {
    if (toXpath === fromXpath) {
        return true;
    }
    const toParts = toXpath.split("/");
    const fromParts = fromXpath.split("/");

    // Are the paths at least in the same parent node ?
    if (toParts.slice(0, -1).join("/") !== fromParts.slice(0, -1).join("/")) {
        return false;
    }

    const nodeIdxRegExp = /(\w+)(\[(\d+)\])?/;
    const toMatch = toParts[toParts.length - 1].match(nodeIdxRegExp);
    const fromMatch = fromParts[fromParts.length - 1].match(nodeIdxRegExp);

    // Are the paths comparable in terms of their node tag ?
    if (fromMatch[1] !== toMatch[1]) {
        return false;
    }

    // Is the position actually referring to the same place ?
    if (position === "after" && parseInt(toMatch[3] || 1) + 1 === parseInt(fromMatch[3] || 1)) {
        return true;
    }
    return false;
}

export function getHooks(el) {
    return [...el.querySelectorAll(".o_web_studio_hook")];
}

export function randomName(baseName) {
    const random =
        Math.floor(Math.random() * 10000).toString(32) + "_" + Number(new Date()).toString(32);
    return `${baseName}_${random}`;
}

// A standardized method to determine if a component is visible
export function studioIsVisible(props) {
    return props.studioIsVisible !== undefined ? props.studioIsVisible : true;
}

export function cleanClickedElements(mainEl) {
    for (const el of mainEl.querySelectorAll(".o-web-studio-editor--element-clicked")) {
        el.classList.remove("o-web-studio-editor--element-clicked");
    }
}

export function useStudioRef(refName = "studioRef", onClick) {
    // create two hooks and call them here?
    const comp = useComponent();
    const ref = useRef(refName);
    useEffect(
        (el) => {
            if (el) {
                el.setAttribute("data-studio-xpath", comp.props.studioXpath);
            }
        },
        () => [ref.el]
    );

    if (onClick) {
        const handler = onClick.bind(comp);
        useEffect(
            (el) => {
                if (el) {
                    el.addEventListener("click", handler, { capture: true });
                    return () => {
                        el.removeEventListener("click", handler);
                    };
                }
            },
            () => [ref.el]
        );
    }
}

export function makeModelErrorResilient(ModelClass) {
    function logError(debug) {
        if (!debug) {
            return;
        }
        console.warn(
            "The onchange triggered an error. It may indicate either a faulty call to onchange, or a faulty model python side"
        );
    }
    return class ResilientModel extends ModelClass {
        setup() {
            super.setup(...arguments);
            const orm = this.orm;
            const debug = this.env.debug;
            this.orm = Object.assign(Object.create(orm), {
                async call(model, method) {
                    if (method === "onchange") {
                        try {
                            return await orm.call.call(orm, ...arguments);
                        } catch {
                            logError(debug);
                        }
                        return { value: {} };
                    }
                    return orm.call.call(orm, ...arguments);
                },
            });
        }
    };
}

export function getWowlFieldWidgets(
    fieldType,
    currentKey = "",
    blacklistedKeys = [],
    debug = false
) {
    const wowlFieldRegistry = registry.category("fields");
    const widgets = [];
    for (const [widgetKey, Component] of wowlFieldRegistry.getEntries()) {
        if (widgetKey !== currentKey) {
            // always show the current widget
            // Widget dosn't explicitly supports the field's type
            if (!Component.supportedTypes || !Component.supportedTypes.includes(fieldType)) {
                continue;
            }
            // Widget is view-specific or is blacklisted
            if (widgetKey.includes(".") || blacklistedKeys.includes(widgetKey)) {
                continue;
            }
            // Widget is not whitelisted
            if (!debug && !SIDEBAR_SAFE_FIELDS.includes(widgetKey)) {
                continue;
            }
        }
        widgets.push([widgetKey, Component.displayName]);
    }
    return sortBy(widgets, (el) => el[1] || el[0]);
}

export function xpathToLegacyXpathInfo(xpath) {
    // eg: /form[1]/field[3]
    // RegExp notice: group 1 : form ; group 2: [1], group 3: 1
    const xpathInfo = [];
    const matches = xpath.matchAll(/\/?(\w+)(\[(\d+)\])?/g);
    for (const m of matches) {
        const info = {
            tag: m[1],
            indice: parseInt(m[3] || 1),
        };
        xpathInfo.push(info);
    }
    return xpathInfo;
}

export function fieldsToChoices(fields, filterCallback = undefined) {
    let values = Object.values(fields);
    if (filterCallback) {
        values = values.filter(filterCallback);
    }

    return values.map((field) => ({
        label: odoo.debug ? `${field.string} (${field.name})` : field.string || field.name,
        value: field.name,
    }));
}

export function getStudioNoFetchFields(_fieldNodes) {
    const fieldNames = [];
    const fieldNodes = [];
    Object.entries(_fieldNodes)
        .filter(([fNode, field]) => field.attrs && field.attrs.studio_no_fetch)
        .forEach(([fNode, field]) => {
            fieldNames.push(field.name);
            fieldNodes.push(fNode);
        });
    return {
        fieldNames,
        fieldNodes,
    };
}

export function useModelConfigFetchInvisible(model) {
    function fixActiveFields(activeFields) {
        const stack = [activeFields];
        while (stack.length) {
            const activeFields = stack.pop();
            for (const activeField of Object.values(activeFields)) {
                if ("related" in activeField) {
                    stack.push(activeField.related.activeFields);
                }
                delete activeField.invisible;
            }
        }
        return activeFields;
    }

    const load = model.load;
    model.load = (...args) => {
        fixActiveFields(model.config.activeFields);
        return load.call(model, ...args);
    };
}

export function getCurrencyField(fieldsGet) {
    const field = Object.entries(fieldsGet).find(([fName, fInfo]) => {
        return fInfo.type === "many2one" && fInfo.relation === "res.currency";
    });
    if (field) {
        return field[0];
    }
}
