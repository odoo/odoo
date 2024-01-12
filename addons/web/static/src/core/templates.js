/** @odoo-module */

import { applyInheritance } from "@web/core/template_inheritance";
import { registry } from "@web/core/registry";

const parser = new DOMParser();
function getParsedTemplate(templateString) {
    const doc = parser.parseFromString(templateString, "text/xml");
    for (const processor of registry.category("template_processors").getAll()) {
        processor(doc);
    }
    return doc.firstChild;
}

function getClone(template) {
    const c = template.cloneNode(true);
    new Document().append(c); // => c is the documentElement of its ownerDocument
    return c;
}

let blockType = null;
let blockId = 0;

const templates = {};
const parsedTemplates = {};
const info = {};
export function registerTemplate(name, url, templateString) {
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
            processedTemplate = applyInheritance(
                inheritFrom ? processedTemplate : getClone(processedTemplate),
                getClone(template),
                url
            );
        }
    }

    return processedTemplate;
}

export function getTemplate(name) {
    return _getTemplate(name);
}
