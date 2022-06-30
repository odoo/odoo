/** @odoo-module **/

import {
    append,
    combineAttributes,
    createElement,
    createTextNode,
    getTag,
} from "@web/core/utils/xml";
import { toStringExpression } from "./utils";

/**
 * @typedef Compiler
 * @property {string} selector
 * @property {(el: Element, params: Record<string, any>) => Element} fn
 */

const { xml } = owl;

const templateIds = Object.create(null);

const BUTTON_CLICK_PARAMS = [
    "name",
    "type",
    "args",
    "context",
    "close",
    "confirm",
    "special",
    "effect",
    "help",
    "modifiers",
    // WOWL SAD: is adding the support for debounce attribute here justified or should we
    // just override compileButton in kanban compiler to add the debounce?
    "debounce",
];
const BUTTON_STRING_PROPS = ["string", "size", "title", "icon"];

/**
 * @param {Element} el
 * @param {string} attr
 * @param {string} string
 */
function appendAttr(el, attr, string) {
    const attrKey = `t-att-${attr}`;
    const attrVal = el.getAttribute(attrKey);
    el.setAttribute(attrKey, appendToStringifiedObject(attrVal, string));
}

/**
 * @param {string} originalTattr
 * @param {string} string
 * @returns {string}
 */
function appendToStringifiedObject(originalTattr, string) {
    const re = /{(.*)}/;
    const oldString = re.exec(originalTattr);

    if (oldString) {
        string = `${oldString[1]},${string}`;
    }
    return `{${string}}`;
}

/**
 * @param {Element} target
 * @param  {...Element} sources
 * @returns {Element}
 */
export function assignOwlDirectives(target, ...sources) {
    for (const source of sources) {
        for (const { name, value } of source.attributes) {
            if (name.startsWith("t-attf-")) {
                const propName = name.slice(7);
                const tAttf = value
                    .split("}}")
                    .map((leftAndExpr) => {
                        const [left, expr] = leftAndExpr.split("{{");
                        const part = toStringExpression(left);
                        return expr ? part + `+${expr}+` : part;
                    })
                    .join("");
                target.setAttribute(propName, tAttf);
            } else if (name.startsWith("t-att-")) {
                const propName = name.slice(6);
                target.setAttribute(propName, value);
            } else if (name.startsWith("t-")) {
                target.setAttribute(name, value);
            }
        }
    }
    return target;
}

/**
 * @param {Element} el
 * @param {Element} compiled
 */
export function copyAttributes(el, compiled) {
    const isComponent = isComponentNode(compiled);
    const classes = el.className;
    if (classes) {
        if (isComponent) {
            const cls = compiled.className;
            compiled.setAttribute("class", cls ? `'${classes} ' + ${cls}` : `'${classes}'`);
        } else {
            compiled.classList.add(...classes.split(/\s+/).filter(Boolean));
        }
    }

    for (const attName of ["style", "placeholder"]) {
        let att = el.getAttribute(attName);
        if (att) {
            if (isComponent) {
                att = toStringExpression(att);
            }
            compiled.setAttribute(attName, att);
        }
    }
}

/**
 * Decodes a string within an attribute into an Object
 * @param  {string} str
 * @return {Object}
 */
export function decodeObjectForTemplate(str) {
    return JSON.parse(decodeURI(str));
}

/**
 * Encodes an object into a string usable inside a pre-compiled template
 * @param  {Object}
 * @return {string}
 */
export function encodeObjectForTemplate(obj) {
    return `"${encodeURI(JSON.stringify(obj))}"`;
}

/**
 * @param {Element} el
 * @param {string} modifierName
 * @returns {boolean | boolean[]}
 */
export function getModifier(el, modifierName) {
    // cf python side def transfer_node_to_modifiers
    // modifiers' string are evaluated to their boolean or array form
    const modifiers = JSON.parse(el.getAttribute("modifiers") || "{}");
    const mod = modifierName in modifiers ? modifiers[modifierName] : false;
    return typeof mod !== "boolean" ? mod : !!mod;
}

/**
 * @param {any} node
 * @returns {string}
 */
function getTitleTag(node) {
    return getTag(node)[0].toUpperCase() + getTag(node).slice(1);
}

/**
 * @param {any} invisibleModifer
 * @param {{ enableInvisible?: boolean }} params
 * @returns {boolean}
 */
export function isAlwaysInvisible(invisibleModifer, params) {
    return !params.enableInvisible && typeof invisibleModifer === "boolean" && invisibleModifer;
}

/**
 * @param {Node} node
 * @returns {boolean}
 */
function isComment(node) {
    return node.nodeType === 8;
}

/**
 * @param {Element} el
 * @returns {boolean}
 */
export function isComponentNode(el) {
    return (
        getTag(el) === getTitleTag(el) ||
        (getTag(el, true) === "t" && "t-component" in el.attributes)
    );
}

/**
 * @param {Node} node
 * @returns {boolean}
 */
export function isTextNode(node) {
    return node.nodeType === 3;
}

/**
 * @param {string} title
 * @returns {Element}
 */
export function makeSeparator(title) {
    const separator = createElement("div");
    separator.className = "o_horizontal_separator";
    separator.textContent = title;
    return separator;
}

export class ViewCompiler {
    constructor() {
        /** @type {number} */
        this.id = 1;
        /** @type {Compiler[]} */
        this.compilers = [
            { selector: "a[type],a[data-type]", fn: this.compileButton },
            { selector: "button", fn: this.compileButton, doNotCopyAttributes: true },
            { selector: "field", fn: this.compileField },
            { selector: "widget", fn: this.compileWidget },
        ];
        this.ctx = { readonly: "props.readonly" };
        this.setup();
    }

    setup() {}

    /**
     * @param {any} invisible
     * @param {Element} compiled
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    applyInvisible(invisible, compiled, params) {
        if (!invisible) {
            return compiled;
        }
        if (typeof invisible === "boolean" && !params.enableInvisible) {
            return;
        }
        if (!params.enableInvisible) {
            combineAttributes(
                compiled,
                "t-if",
                `!evalDomainFromRecord(props.record,${JSON.stringify(invisible)})`,
                " and "
            );
        } else {
            appendAttr(compiled, "class", `o_invisible_modifier:${invisible}`);
        }
        return compiled;
    }

    /**
     * @param {Element} xmlElement
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compile(xmlElement, params = {}) {
        const newRoot = createElement("t");
        const child = this.compileNode(xmlElement, params);
        return append(newRoot, child);
    }

    /**
     * @param {Node} node
     * @param {Record<string, any>} params
     * @returns {Element | Text | void}
     */
    compileNode(node, params = {}, evalInvisible = true) {
        if (isComment(node)) {
            return;
        }
        if (isTextNode(node)) {
            return createTextNode(node.nodeValue);
        }

        let invisible;
        if (evalInvisible) {
            invisible = getModifier(node, "invisible");
            if (isAlwaysInvisible(invisible, params)) {
                return;
            }
        }

        const compiler = this.compilers.find((cp) => node.matches(cp.selector));
        let compiledNode;
        if (compiler) {
            compiledNode = compiler.fn.call(this, node, params);
            if (!compiler.doNotCopyAttributes && compiledNode) {
                copyAttributes(node, compiledNode);
            }
        } else {
            compiledNode = this.compileGenericNode(node, params);
        }

        if (evalInvisible && compiledNode) {
            compiledNode = this.applyInvisible(invisible, compiledNode, params);
        }
        return compiledNode;
    }

    //-----------------------------------------------------------------------------
    // Compilers
    //-----------------------------------------------------------------------------

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileButton(el, params) {
        let tag = getTag(el, true);
        const type = el.getAttribute("type");
        if (tag === "a" && type === "url") {
            tag = "button";
        }
        const button = createElement("ViewButton", {
            tag: toStringExpression(tag),
            record: `props.record`,
        });

        assignOwlDirectives(button, el);

        const clickParams = {};
        for (const { name, value } of el.attributes) {
            if (BUTTON_CLICK_PARAMS.includes(name)) {
                clickParams[name] = value;
            } else if (BUTTON_STRING_PROPS.includes(name)) {
                button.setAttribute(name, toStringExpression(value));
            }
        }

        button.setAttribute("clickParams", JSON.stringify(clickParams));
        button.setAttribute("className", toStringExpression(el.className));
        el.removeAttribute("class");
        button.removeAttribute("class");

        // Button's body
        const buttonContent = [];
        for (const child of el.childNodes) {
            const compiled = this.compileNode(child, params);
            if (compiled) {
                buttonContent.push(compiled);
            }
        }
        if (buttonContent.length) {
            const contentSlot = createElement("t");
            contentSlot.setAttribute("t-set-slot", "contents");
            append(button, contentSlot);
            for (const buttonChild of buttonContent) {
                append(contentSlot, buttonChild);
            }
        }
        return button;
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileField(el) {
        const fieldName = el.getAttribute("name");
        const fieldId = el.getAttribute("field_id") || fieldName;

        const field = createElement("Field");
        field.setAttribute("id", `'${fieldId}'`);
        field.setAttribute("name", `'${fieldName}'`);
        field.setAttribute("record", `props.record`);
        field.setAttribute("fieldInfo", `props.archInfo.fieldNodes['${fieldId}']`);

        if (el.hasAttribute("widget")) {
            field.setAttribute("type", `'${el.getAttribute("widget")}'`);
        }

        return field;
    }

    /**
     * @param {Element} el
     * @param {Record<string, any>} params
     * @returns {Element}
     */
    compileGenericNode(el, params) {
        const compiled = createElement(el.nodeName);
        const metaAttrs = ["modifiers", "attrs", "invisible", "readonly"];
        for (const attr of el.attributes) {
            if (metaAttrs.includes(attr.name)) {
                continue;
            }
            compiled.setAttribute(attr.name, attr.value);
        }
        for (const child of el.childNodes) {
            append(compiled, this.compileNode(child, params));
        }
        if (el.hasAttribute("t-foreach") && !el.hasAttribute("t-key")) {
            compiled.setAttribute("t-key", `${el.getAttribute("t-as")}_index`);
            console.warn(`Missing attribute "t-key" in "t-foreach" statement.`);
        }
        return compiled;
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileWidget(el) {
        const attrs = {};
        const props = { record: `props.record`, readonly: this.ctx.readonly };
        for (const { name, value } of el.attributes) {
            switch (name) {
                case "class":
                case "name": {
                    props[name] = `'${value}'`;
                    break;
                }
                case "modifiers": {
                    attrs.modifiers = JSON.parse(value || "{}");
                    break;
                }
                default: {
                    attrs[name] = value;
                }
            }
        }
        props.node = encodeObjectForTemplate({ attrs });
        const widget = createElement("Widget", props);
        return assignOwlDirectives(widget, el);
    }
}

/**
 * @param {typeof ViewCompiler} ViewCompiler
 * @param {string} templateKey
 * @param {Element} xmlDoc
 * @param {Record<string, any>} [params]
 * @returns {string}
 */
export function useViewCompiler(ViewCompiler, templateKey, xmlDoc, params) {
    // Creates a new compiled template if the given template key hasn't been
    // compiled already.
    if (templateKey === undefined) {
        throw new Error("templateKey can not be Undefined!");
    }
    if (!templateIds[templateKey]) {
        const compiledDoc = new ViewCompiler().compile(xmlDoc, params);
        templateIds[templateKey] = xml`${compiledDoc.outerHTML}`;
    }
    return templateIds[templateKey];
}
