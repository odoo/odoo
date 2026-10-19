import { Base } from "../models/related_models";
import { RAW_SYMBOL } from "../models/related_models/utils";
import { WithLazyGetterTrap } from "../../lazy_getter";
import { toRaw } from "@odoo/owl";

// https://www.mattzeunert.com/2016/02/19/custom-chrome-devtools-object-formatters.html

/**
 * Custom Chrome DevTools Object Formatters
 * This module registers custom formatters for Chrome DevTools console to improve
 * the debugging experience by formatting some POS objects (ModelRecords,lazyGetter, ...)  in a more readable way.
 */

export function init() {
    const formatters = [
        baseObjectFormatter(),
        modelFormatter(),
        modelsFormatter(),
        lazyGetterFormatter(),
        immutableFormatter(),
        reactiveArrayFormatter(),
    ];
    window.devtoolsFormatters = window.devtoolsFormatters
        ? [...window.devtoolsFormatters, ...formatters]
        : formatters;
}

function baseObjectFormatter() {
    return {
        header(obj) {
            if (!(obj instanceof Base)) {
                return null;
            }
            const name =
                obj.constructor.name === "ModelRecord" ? obj.model.name : obj.constructor.name;
            return ["div", {}, name + " #" + obj.id];
        },
        hasBody: () => true,
        body: (obj) => ["div", {}, ...formatBaseInstance(obj)],
    };
}

function modelsFormatter() {
    return {
        header(obj) {
            return obj.constructor?.name === "Models" && obj._loadData
                ? createSubObjectBlock(`Models`, getDebugObject(toRaw(obj)), "")
                : null;
        },
        hasBody: () => false,
    };
}

function modelFormatter() {
    return {
        header(obj) {
            return obj.constructor?.name === "Model" && obj.models
                ? createSubObjectBlock(
                      `Model(${obj.name})`,
                      { name: obj.name, fields: toRaw(obj.fields) },
                      ""
                  )
                : null;
        },
        hasBody: () => false,
    };
}

function immutableFormatter() {
    return {
        header(obj) {
            return obj.__deepImmutable
                ? createSubObjectBlock("ImmutableObject", getDebugObject(toRaw(obj)), "")
                : null;
        },
        hasBody: () => false,
    };
}

function reactiveArrayFormatter() {
    return {
        header(obj) {
            return Array.isArray(obj) && toRaw(obj) !== obj ? ["div", {}, formatValue(obj)] : null;
        },
        hasBody: () => false,
    };
}

function lazyGetterFormatter() {
    return {
        header(obj) {
            if (!(obj instanceof WithLazyGetterTrap)) {
                return null;
            }
            return createSubObjectBlock(obj.constructor.name, getDebugObject(toRaw(obj)), "");
        },
        hasBody: () => false,
    };
}

function formatBaseInstance(obj) {
    const blocks = [];
    if (obj[RAW_SYMBOL]) {
        blocks.push(createSubObjectBlock("[raw]", toRaw(obj[RAW_SYMBOL])));
    }
    const relations = getRelations(obj);
    if (Object.keys(relations).length) {
        blocks.push(createSubObjectBlock("[relations]", relations));
    }
    if (obj.uiState) {
        blocks.push(createSubObjectBlock("[uiState]", toRaw(obj.uiState)));
    }
    const dismissFields = new Set([
        "_dirty",
        "model",
        "models",
        "uiState",
        "raw",
        ...Object.keys(obj.model.fields),
    ]);

    const debugObject = getDebugObject(obj, dismissFields);
    if (debugObject) {
        blocks.push(createSubObjectBlock("[other props]", debugObject));
    }
    // blocks.push(createSubBlock("(dirty)", obj._dirty));
    // blocks.push(createSubObjectBlock("[model]", obj.model));
    return blocks;
}

function createSubObjectBlock(name, obj, style = "color:#1E90FF") {
    return ["div", {}, ["div", { style: style }, name], ["object", { object: obj }]];
}

function getRelations(obj) {
    return Object.fromEntries(
        Object.entries(obj.model.fields)
            .filter(([_, value]) => value.relation && !value.dummy)
            .map(([field]) => [field, obj[field]])
    );
}

function formatValue(val) {
    if (typeof val === "number" || typeof val === "boolean") {
        return ["span", {}, val];
    }
    if (typeof val === "string") {
        return ["span", {}, JSON.stringify(val)];
    }
    if (val instanceof Set || Array.isArray(val)) {
        return ["object", { object: toRaw([...val]) }];
    }
    if (typeof val === "object") {
        return ["object", { object: toRaw(val) }];
    }
    return ["span", {}, "" + val];
}

function getDebugObject(obj, dismissFields = new Set()) {
    const debugObject = {};
    let hasValue = false;

    while (obj && obj !== Object.prototype) {
        Object.entries(Object.getOwnPropertyDescriptors(obj)).forEach(([key, descriptor]) => {
            if (dismissFields.has(key) || key.startsWith("__lazy")) {
                return;
            }

            if ("value" in descriptor && typeof descriptor.value !== "function") {
                debugObject[key] = descriptor.value;
                hasValue = true;
            } else if (typeof descriptor.get === "function") {
                Object.defineProperty(debugObject, key, { get: () => obj[key] });
                hasValue = true;
            }
        });
        obj = Object.getPrototypeOf(obj);
    }
    return hasValue ? debugObject : null;
}
