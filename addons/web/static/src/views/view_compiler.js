import {
    append,
    combineAttributes,
    createElement,
    createTextNode,
    getTag,
} from "@web/core/utils/xml";
import { toStringExpression, BUTTON_CLICK_PARAMS } from "./utils";

/**
 * @typedef Compiler
 * @property {string} selector
 * @property {(el: Element, params: Record<string, any>) => Element} fn
 * @property {string} [class]
 * @property {boolean} [doNotCopyAttributes]
 */

import { xml } from "@odoo/owl";

const BUTTON_STRING_PROPS = ["string", "size", "title", "icon", "id", "disabled"];
const INTERP_REGEXP = /(\{\{|#\{)(.*?)(\}{1,2})/g;

/**
 * @param {string} str
 * @returns {string} the interpolated string to be injected into a component's node props.
 */
export function toInterpolatedStringExpression(str) {
    const matches = str.matchAll(INTERP_REGEXP);
    const parts = [];
    let searchString = str;
    for (const [match, head, expr] of matches) {
        const index = searchString.indexOf(head);
        const left = searchString.slice(0, index);
        if (left) {
            parts.push(toStringExpression(left));
        }
        parts.push(`(${expr})`);
        searchString = searchString.slice(index + match.length);
    }
    parts.push(toStringExpression(searchString));
    return parts.join("+");
}

/**
 * @param {Element} el
 * @param {string} attr
 * @param {string} string
 */
export function appendAttr(el, attr, string) {
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
                const interpolatedExpression = toInterpolatedStringExpression(value);
                target.setAttribute(propName, interpolatedExpression);
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

    let att = el.getAttribute("style");
    if (att) {
        if (isComponent) {
            att = toStringExpression(att);
        }
        compiled.setAttribute("style", att);
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
    return el.getAttribute(modifierName);
}

/**
 * @param {any} node
 * @returns {string}
 */
function getTitleTag(node) {
    return getTag(node)[0].toUpperCase() + getTag(node).slice(1);
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
    separator.className = "o_horizontal_separator mt-4 mb-3 text-uppercase fw-bolder small";
    separator.textContent = title;
    return separator;
}

export class ViewCompiler {
    constructor(templates) {
        /** @type {number} */
        this.id = 1;
        /** @type {Compiler[]} */
        this.compilers = [
            {
                selector: "a[type]:not([data-bs-toggle]),a[data-type]:not([data-bs-toggle])",
                fn: this.compileButton,
            },
            {
                selector: "button:not([data-bs-toggle])",
                fn: this.compileButton,
                doNotCopyAttributes: true,
            },
            { selector: "field", fn: this.compileField },
            { selector: "widget", fn: this.compileWidget },
        ];
        this.templates = templates;
        this.ctx = { readonly: "__comp__.props.readonly" };

        this.owlDirectiveRegexesWhitelist = this.constructor.OWL_DIRECTIVE_WHITELIST.map(
            (d) => new RegExp(d)
        );
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
        if (!invisible || invisible === "False") {
            return compiled;
        }
        if (invisible === "True" || invisible === "1") {
            return;
        }
        const recordExpr = params.recordExpr || "__comp__.props.record";
        let isVisileExpr = `!__comp__.evaluateBooleanExpr(${JSON.stringify(
            invisible
        )},${recordExpr}.evalContextWithVirtualIds)`;
        if (compiled.hasAttribute("t-if")) {
            const formerTif = compiled.getAttribute("t-if");
            isVisileExpr = `( ${formerTif} ) and ${isVisileExpr}`;
        }
        compiled.setAttribute("t-if", isVisileExpr);
        return compiled;
    }

    /**
     * @param {string} key
     * @param {Record<string, any>} params
     * @returns {string}
     */
    compile(key, params = {}) {
        const root = this.templates[key].cloneNode(true);
        const child = this.compileNode(root, params);
        const newRoot = createElement("t", child ? [child] : []);
        newRoot.setAttribute("t-translation", "off");
        return newRoot;
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

        if (node.hasAttribute("t-translation")) {
            node.removeAttribute("t-translation");
        }
        this.validateNode(node);
        let invisible;
        if (evalInvisible) {
            invisible = getModifier(node, "invisible");
            if (!params.compileInvisibleNodes && (invisible === "True" || invisible === "1")) {
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
        const recordExpr = params.recordExpr || "__comp__.props.record";
        const button = createElement("ViewButton", {
            tag: toStringExpression(tag),
            record: recordExpr,
        });

        assignOwlDirectives(button, el);

        combineAttributes(
            button,
            "className",
            [toStringExpression(el.className), button.className],
            "+` `+"
        );
        el.removeAttribute("class");
        button.removeAttribute("class");

        const clickParams = {};
        const attrs = {};
        for (const { name, value } of el.attributes) {
            if (BUTTON_CLICK_PARAMS.includes(name)) {
                clickParams[name] = value;
            } else if (BUTTON_STRING_PROPS.includes(name)) {
                button.setAttribute(name, toStringExpression(value));
            } else if (!name.startsWith("t-")) {
                attrs[name] = value;
            }
        }

        button.setAttribute("clickParams", JSON.stringify(clickParams));
        button.setAttribute("attrs", JSON.stringify(attrs));

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
    compileField(el, params) {
        const fieldName = el.getAttribute("name");
        const fieldId = el.getAttribute("field_id");

        const field = createElement("Field");
        const recordExpr = params.recordExpr || "__comp__.props.record";
        field.setAttribute("id", `'${fieldId}'`);
        field.setAttribute("name", `'${fieldName}'`);
        field.setAttribute("record", recordExpr);
        field.setAttribute("fieldInfo", `__comp__.props.archInfo.fieldNodes['${fieldId}']`);
        field.setAttribute(
            "readonly",
            `__comp__.props.archInfo.activeActions?.edit === false and !${recordExpr}.isNew`
        );

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
        const compiled = createElement(el.nodeName.toLowerCase());
        const metaAttrs = ["column_invisible", "invisible", "readonly", "required"];
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
        const widgetId = el.getAttribute("widget_id");
        const props = { record: "__comp__.props.record" };
        if (el.hasAttribute("name")) {
            props.name = `'${el.getAttribute("name")}'`;
        }
        if (el.hasAttribute("class")) {
            props.className = `'${el.getAttribute("class")}'`;
        }
        props.widgetInfo = `__comp__.props.archInfo.widgetNodes['${widgetId}']`;
        const widget = createElement("Widget", props);
        return assignOwlDirectives(widget, el);
    }

    validateNode(node) {
        // detect attributes not in whitelist, starting with t-
        const attributes = Object.values(node.attributes).map((attr) => attr.name);
        const regexes = this.owlDirectiveRegexesWhitelist;
        for (const attr of attributes) {
            if (attr.startsWith("t-") && !regexes.some((regex) => regex.test(attr))) {
                console.warn(`Forbidden directive ${attr} used in arch`);
            }
        }
    }
}
ViewCompiler.OWL_DIRECTIVE_WHITELIST = [];

let templateCache = Object.create(null);
/**
 * @param {typeof ViewCompiler} ViewCompiler
 * @param {string} key
 * @param {Record<string, Element>} templates
 * @param {Record<string, any>} [params]
 * @returns {Record<string, string>}
 */
export function useViewCompiler(ViewCompiler, templates, params) {
    const compiledTemplates = {};
    let compiler;
    for (const tname in templates) {
        const key = `${ViewCompiler.name}/${templates[tname].outerHTML}`;
        if (!templateCache[key]) {
            compiler = compiler || new ViewCompiler(templates);
            templateCache[key] = xml`${compiler.compile(tname, params).outerHTML}`;
        }
        compiledTemplates[tname] = templateCache[key];
    }
    return compiledTemplates;
}

/*
 * clear the view compiler's cache.
 * FIXME: that function only purges the compiler's cache and NOT the cache in owl's app.
 * the owl.xml function creates an internal template each time, so the cache is here to prevent
 * creating new owl templates every time. If we clear the cache, new templates WILL be created,
 * even if the arch to compile is the same.
 * This is how a memory leak occurs. :-)
 */
export function resetViewCompilerCache() {
    templateCache = Object.create(null);
}
