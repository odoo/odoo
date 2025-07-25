import {
    applyContextToTextNode,
    applyInheritance,
    deepClone,
} from "@web/core/template_inheritance";

function getClone(template) {
    const c = deepClone(template);
    new Document().append(c); // => c is the documentElement of its ownerDocument
    return c;
}

function getParsedTemplate(templateString) {
    const doc = parser.parseFromString(templateString, "text/xml");
    for (const processor of templateProcessors) {
        processor(doc);
    }
    return doc.firstChild;
}

function _getTemplate(name, blockId = null) {
    if (!(name in parsedTemplates)) {
        if (!(name in templates)) {
            return null;
        }
        const templateString = templates[name];
        parsedTemplates[name] = getParsedTemplate(templateString);
        const inheritFrom = parsedTemplates[name].getAttribute("t-inherit");
        if (!inheritFrom) {
            const addon = info[name].url.split("/")[1];
            parsedTemplates[name].setAttribute("t-translation-context", addon);
        }
    }
    let processedTemplate = parsedTemplates[name];

    const inheritFrom = processedTemplate.getAttribute("t-inherit");
    if (inheritFrom) {
        const parentTemplate = _getTemplate(inheritFrom, blockId || info[name].blockId);
        if (!parentTemplate) {
            throw new Error(
                `Constructing template ${name}: template parent ${inheritFrom} not found`
            );
        }
        const element = getClone(processedTemplate);
        processedTemplate = applyInheritance(getClone(parentTemplate), element, info[name].url);
        if (processedTemplate.tagName !== element.tagName) {
            const temp = processedTemplate;
            processedTemplate = new Document().createElement(element.tagName);
            processedTemplate.append(...temp.childNodes);
        }
        for (const { name, value } of element.attributes) {
            if (!["t-inherit", "t-inherit-mode"].includes(name)) {
                processedTemplate.setAttribute(name, value);
            }
        }
    }

    let cloned = false;
    for (const otherBlockId in templateExtensions[name] || {}) {
        if (blockId && otherBlockId > blockId) {
            break;
        }
        if (!(name in parsedTemplateExtensions)) {
            parsedTemplateExtensions[name] = {};
        }
        if (!(otherBlockId in parsedTemplateExtensions[name])) {
            parsedTemplateExtensions[name][otherBlockId] = [];
            for (const { templateString, url } of templateExtensions[name][otherBlockId]) {
                parsedTemplateExtensions[name][otherBlockId].push({
                    template: getParsedTemplate(templateString),
                    url,
                });
            }
        }
        for (const { template, url } of parsedTemplateExtensions[name][otherBlockId]) {
            if (!urlFilters.every((filter) => filter(url))) {
                continue;
            }
            if (!inheritFrom && !cloned) {
                cloned = true;
                processedTemplate = getClone(processedTemplate);
            }
            processedTemplate = applyInheritance(processedTemplate, getClone(template), url);
        }
    }

    return processedTemplate;
}

function isRegistered(...args) {
    const key = JSON.stringify([...args]);
    if (registered.has(key)) {
        return true;
    }
    registered.add(key);
    return false;
}

const info = Object.create(null);
const parsedTemplateExtensions = Object.create(null);
const parsedTemplates = Object.create(null);
const parser = new DOMParser();
/** @type {Map<string, Element>} */
const processedTemplates = new Map();
const registered = new Set();
/** @type {Record<string, Record<number, ({ templateString: string, url: string })[]>>} */
const templateExtensions = Object.create(null);
/** @type {((document: Document) => void)[]} */
const templateProcessors = [];
/** @type {Record<string, string>} */
const templates = Object.create(null);
let blockType = null;
let blockId = 0;
/** @type {((url: string) => boolean)[]} */
let urlFilters = [];

export function checkPrimaryTemplateParents(namesToCheck) {
    const missing = new Set(namesToCheck.filter((name) => !(name in templates)));
    if (missing.size) {
        console.error(`Missing (primary) parent templates: ${[...missing].join(", ")}`);
    }
}

export function clearProcessedTemplates() {
    processedTemplates.clear();
}

/**
 * @param {string} name
 */
export function getTemplate(name) {
    if (!processedTemplates.has(name)) {
        processedTemplates.set(name, _getTemplate(name));
        applyContextToTextNode();
    }
    return processedTemplates.get(name);
}

export function registerTemplate(name, url, templateString) {
    if (isRegistered(...arguments)) {
        return;
    }
    if (blockType !== "templates") {
        blockType = "templates";
        blockId++;
    }
    if (name in templates && (info[name].url !== url || templates[name] !== templateString)) {
        throw new Error(`Template ${name} already exists`);
    }
    templates[name] = templateString;
    info[name] = { blockId, url };

    return () => {
        delete templates[name];
        delete info[name];
        delete parsedTemplates[name];
        delete parsedTemplateExtensions[name];
        processedTemplates.delete(name);
        registered.delete(JSON.stringify([...arguments]));
    };
}

export function registerTemplateExtension(inheritFrom, url, templateString) {
    if (isRegistered(...arguments)) {
        return;
    }
    if (blockType !== "extensions") {
        blockType = "extensions";
        blockId++;
    }
    if (!templateExtensions[inheritFrom]) {
        templateExtensions[inheritFrom] = [];
    }
    if (!templateExtensions[inheritFrom][blockId]) {
        templateExtensions[inheritFrom][blockId] = [];
    }
    templateExtensions[inheritFrom][blockId].push({
        templateString,
        url,
    });

    return () => {
        const index = templateExtensions[inheritFrom]?.[blockId]?.findIndex(
            (ext) => ext.templateString === templateString && ext.url === url
        );
        if (Number.isInteger(index) && index > -1) {
            templateExtensions[inheritFrom][blockId].splice(index, 1);
        }
        registered.delete(JSON.stringify([...arguments]));
    };
}

/**
 * @param {(document: Document) => void} processor
 */
export function registerTemplateProcessor(processor) {
    templateProcessors.push(processor);
}

/**
 * @param {typeof urlFilters} filters
 */
export function setUrlFilters(filters) {
    const prev = urlFilters;
    urlFilters = filters;
    return () => {
        urlFilters = prev;
    };
}
