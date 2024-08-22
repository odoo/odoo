import { applyInheritance } from "@web/core/template_inheritance";

const parser = new DOMParser();
/** @type {((document: Document) => void)[]} */
const templateProcessors = [];
/** @type {((url: string) => boolean)[]} */
let urlFilters = [];
function getParsedTemplate(templateString) {
    const doc = parser.parseFromString(templateString, "text/xml");
    for (const processor of templateProcessors) {
        processor(doc);
    }
    return doc.firstChild;
}

function getClone(template) {
    const c = template.cloneNode(true);
    new Document().append(c); // => c is the documentElement of its ownerDocument
    return c;
}

const registered = new Set();
function isRegistered(...args) {
    const key = JSON.stringify([...args]);
    if (registered.has(key)) {
        return true;
    }
    registered.add(key);
    return false;
}

let blockType = null;
let blockId = 0;

const templates = {};
const parsedTemplates = {};
const info = {};
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
}

const templateExtensions = {};
const parsedTemplateExtensions = {};
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
    urlFilters = filters;
}

function _getTemplate(name, blockId = null) {
    if (!(name in parsedTemplates)) {
        if (!(name in templates)) {
            return null;
        }
        const templateString = templates[name];
        parsedTemplates[name] = getParsedTemplate(templateString);
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
            processedTemplate = applyInheritance(
                inheritFrom ? processedTemplate : getClone(processedTemplate),
                getClone(template),
                url
            );
        }
    }

    return processedTemplate;
}

/** @type {Record<string, Element>} */
let processedTemplates = {};

/**
 * @param {string} name
 */
export function getTemplate(name) {
    if (!processedTemplates[name]) {
        processedTemplates[name] = _getTemplate(name);
    }
    return processedTemplates[name];
}

export function clearProcessedTemplates() {
    processedTemplates = {};
}

export function checkPrimaryTemplateParents(namesToCheck) {
    const missing = new Set(namesToCheck.filter((name) => !(name in templates)));
    if (missing.size) {
        console.error(`Missing (primary) parent templates: ${[...missing].join(", ")}`);
    }
}
export const __test__allTemplates = templates;
