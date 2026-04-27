import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { computeXpath, applyInvisible } from "../xml_utils";
import { createElement, getTag } from "@web/core/utils/xml";
import { isComponentNode } from "@web/views/view_compiler";

const interestingSelector = [
    "div",
    "aside",
    "footer",
    "field:not([data-used-by])",
    "main",
    "kanban",
    "widget",
    "a",
    "button",
].join(", ");

/**
 * @param {Element} el
 * @returns {string}
 */
function getElementXpath(el) {
    const xpath = el.getAttribute("studioXpath");
    if (isComponentNode(el)) {
        return xpath;
    }
    return `"${xpath}"`;
}

/**
 * @param {Element} el
 * @param {string} xpath
 */
function setElementXpath(el, xpath) {
    if (isComponentNode(el)) {
        el.setAttribute("studioXpath", `'${xpath}'`);
    } else {
        el.setAttribute("studioXpath", xpath);
    }
}

export class KanbanEditorCompiler extends KanbanCompiler {
    applyInvisible(invisible, compiled, params) {
        return applyInvisible(invisible, compiled, params);
    }

    /**
     * Wrap the given node with a <t> element containing hooks before and after it.
     * @param {Element} node - The node to wrap with hooks
     * @param {string} type - The type of the hook
     * @param {string} template - The template to use for the hook
     * @param {boolean} insertBefore - Whether to insert the before hook
     * @returns {Element} The wrapped node
     */
    addStudioHook(node, type, template, { structures, wrap = false } = {}) {
        const xpath = getElementXpath(node);
        if (wrap) {
            const studioHookBefore = createElement("StudioHook", {
                xpath,
                position: "'before'",
                type: `'${type}'`,
                subTemplate: `'${template}'`,
                structures,
            });
            node.insertAdjacentElement("beforebegin", studioHookBefore);
        }
        const studioHookAfter = createElement("StudioHook", {
            xpath,
            position: "'after'",
            type: `'${type}'`,
            subTemplate: `'${template}'`,
            structures,
        });
        node.insertAdjacentElement("afterend", studioHookAfter);
    }

    wrapNodesInMain(node) {
        const elementsToWrap = Array.from(node.children).filter((e) => {
            if (e.tagName === "widget") {
                return e.getAttribute("name") !== "web_ribbon";
            }
            if (e.tagName === "t" && e.getAttribute("t-name") === "menu") {
                return false;
            }
            return !["aside"].includes(e.tagName);
        });
        return createElement("main", elementsToWrap);
    }

    compile(key, params = {}) {
        const xml = this.templates[key];
        const interestingArchNodes = [...xml.querySelectorAll(interestingSelector)];
        for (const el of interestingArchNodes) {
            const xpath = computeXpath(el, "kanban");
            setElementXpath(el, xpath);
        }
        const compiled = super.compile(key, params);
        return compiled;
    }

    compileButton(el, params) {
        const compiled = super.compileButton(...arguments);
        setElementXpath(compiled, el.getAttribute("studioXpath"));
        return compiled;
    }

    compileCard(node, params) {
        const mainNode = node.querySelector("main");
        if (!mainNode) {
            // to ease the addition of studio hooks in the UI, we make sure the kanban card contains a <main> node,
            // which wraps the content of the card, even if the original template didn't compile this node
            const mainEl = this.wrapNodesInMain(node);
            setElementXpath(mainEl, "kanban");
            node.append(mainEl);
        }
        const asideNode = node.querySelector("aside");
        const ribbonNode = node.querySelector("widget[name='web_ribbon']");
        const compiledCard = super.compileNode(node, params);
        const compiledMain = compiledCard.querySelector("main");
        if (!ribbonNode) {
            this.addStudioHook(compiledMain, "ribbon", "kanbanRibbon");
        }
        if (!asideNode) {
            this.addStudioHook(compiledMain, "kanbanAsideHook", "kanbanAsideHook", { wrap: true });
        }
        return compiledCard;
    }

    compileField(el, params) {
        const compiled = super.compileField(...arguments);
        if (!el.hasAttribute("widget")) {
            compiled.classList.add("o-web-studio-editor--element-clickable");

            // Set empty class
            const fieldName = el.getAttribute("name");
            const recordValueExpr = `__comp__.props.record.data["${fieldName}"]`;
            const isEmptyExpr = `__comp__.isFieldValueEmpty(${recordValueExpr})`;
            compiled.setAttribute(
                "t-attf-class",
                `{{ ${isEmptyExpr} ? "o_web_studio_widget_empty" : "" }}`
            );
            const fieldNameExpr = `__comp__.props.record.fields["${fieldName}"].string`;
            const originalTOut = compiled.getAttribute("t-out");
            compiled.setAttribute("t-out", `${isEmptyExpr} ? ${fieldNameExpr} : ${originalTOut}`);
        } else {
            compiled.setAttribute("hasEmptyPlaceholder", true);
        }
        return compiled;
    }

    compileInnerSection(compiled) {
        const interestingNodes = [...compiled.querySelectorAll("[studioXpath]")].filter(
            (e) => e.getAttribute("studioXpath") !== "null" && !e.closest("ViewButton")
        );
        const otherNodes = [...compiled.querySelectorAll("div[studioXpath]")].filter(
            (e) => !e.getAttribute("t-out")
        );
        for (const child of otherNodes) {
            // add a visual indication around structuring elements of the main element
            child.classList.add("o_inner_section");
            child.classList.add("o-web-studio-editor--element-clickable");
        }
        for (const child of interestingNodes) {
            if (
                [...child.getAttributeNames()].filter((e) =>
                    ["t-if", "t-elif", "t-else"].includes(e)
                ).length
            ) {
                // Don't append a studio hook if a condition is on the tag itself
                // otherwise it may cause inconsistencies in the arch itself
                // ie `<field t-elif="someConditon" /><field name="newField" /><t t-else=""/>` would be invalid
                continue;
            }
            this.addStudioHook(
                child,
                "field",
                // for inline display, the studio hook must be a span to keep the current look
                child.tagName === "span" ? "kanbanInline" : "defaultTemplate",
                { structures: `'field'`, wrap: true }
            );
        }
        if (!interestingNodes.length) {
            const hook = createElement("StudioHook", {
                xpath: `"${compiled.getAttribute("studioXpath")}"`,
                position: "'inside'",
                type: "'field'",
                subTemplate: "defaultTemplate",
                structures: `'field'`,
            });
            compiled.appendChild(hook);
        }
    }

    compileNode(node, params) {
        if (node.tagName === "field" && node.hasAttribute("data-used-by")) {
            return;
        }
        let compiled;
        if (node.getAttribute?.("t-name") === "card") {
            compiled = this.compileCard(node);
        } else {
            compiled = super.compileNode(node, { ...params, compileInvisibleNodes: true });
        }
        if (["aside", "footer"].includes(getTag(node))) {
            compiled.classList.add("o_inner_section");
            compiled.classList.add("o-web-studio-editor--element-clickable");
            this.compileInnerSection(compiled);
        } else if (getTag(node) === "main") {
            this.compileInnerSection(compiled);
            if (!compiled.querySelector("footer")) {
                const footerHook = createElement("StudioHook", {
                    xpath: `"${compiled.getAttribute("studioXpath")}"`,
                    position: "'after'",
                    type: `'footer'`,
                    subTemplate: `'defaultTemplate'`,
                    structures: `'footer'`,
                });
                compiled.appendChild(footerHook);
            }
        }
        // Propagate the xpath to the compiled template for most nodes.
        if (node.nodeType === 1 && compiled && !compiled.attributes.studioXpath) {
            setElementXpath(compiled, node.getAttribute("studioXpath"));
        }
        return compiled;
    }
}
