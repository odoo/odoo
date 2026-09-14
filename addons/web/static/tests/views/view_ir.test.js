// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { VIEW_IR_FIXTURE } from "@web/../tests/views/view_ir_fixture";
import { parseXML } from "@web/core/utils/dom/xml";
import { elementToIR, irToElement } from "@web/views/ir/view_ir";

describe.current.tags("headless");

const serializer = new XMLSerializer();

/** @param {Element} element */
function serialize(element) {
    return serializer.serializeToString(element);
}

/**
 * What the IR keeps of a parsed arch: comments and processing instructions
 * in place, CDATA read as text, adjacent text merged — the same on both sides.
 *
 * @param {Element} element
 */
function normalized(element) {
    const doc = element.ownerDocument;
    const walker = doc.createTreeWalker(element, NodeFilter.SHOW_CDATA_SECTION);
    /** @type {CDATASection[]} */
    const nodes = [];
    while (walker.nextNode()) {
        nodes.push(/** @type {CDATASection} */ (walker.currentNode));
    }
    for (const node of nodes) {
        node.replaceWith(doc.createTextNode(node.data));
    }
    element.normalize();
    return element;
}

/** @param {Element} element */
function countNodes(element) {
    return 1 + [...element.children].reduce((n, child) => n + countNodes(child), 0);
}

describe("view IR fixture — the server and the client read the same tree", () => {
    for (const entry of VIEW_IR_FIXTURE) {
        test(entry.name, () => {
            const parsed = parseXML(entry.arch);
            expect(elementToIR(parsed)).toEqual(entry.ir);
            const built = irToElement(entry.ir);
            expect(serialize(built)).toBe(serialize(normalized(parsed)));
            expect(countNodes(built)).toBe(countNodes(parsed));
        });
    }
});

describe("irToElement", () => {
    test("builds a namespace-free XML element, not an HTML one", () => {
        const element = irToElement({
            kind: "form",
            attrs: { string: "A" },
            children: [{ kind: "Field", attrs: { name: "x" } }],
        });
        expect(element.namespaceURI).toBe(null);
        expect(element.ownerDocument.contentType).toBe("application/xml");
        expect(element.firstElementChild?.tagName).toBe("Field");
    });

    test("applies the text hook to text, tails and attribute values", () => {
        const element = irToElement(
            {
                kind: "form",
                attrs: { placeholder: "a&nbsp;b" },
                text: "x&nbsp;",
                children: [{ kind: "span", tail: "&nbsp;y" }],
            },
            { text: (value) => value.replaceAll("&nbsp;", " ") },
        );
        expect(element.getAttribute("placeholder")).toBe("a b");
        expect(element.firstChild?.textContent).toBe("x ");
        expect(element.lastChild?.textContent).toBe(" y");
    });

    test("declares namespaces where the IR declares them", () => {
        const element = irToElement({
            kind: "div",
            children: [
                {
                    kind: "{http://www.w3.org/2000/svg}svg",
                    nsmap: { "": "http://www.w3.org/2000/svg" },
                    children: [
                        {
                            kind: "{http://www.w3.org/2000/svg}circle",
                            attrs: { r: "1" },
                        },
                    ],
                },
            ],
        });
        expect(serialize(element)).toBe(
            '<div><svg xmlns="http://www.w3.org/2000/svg"><circle r="1"/></svg></div>',
        );
    });
});

describe("elementToIR", () => {
    test("omits empty members and keeps a comment where the arch had it", () => {
        const ir = elementToIR(
            parseXML("<list> a <!-- c --> b <field name='x'/> d <?pi e?></list>"),
        );
        expect(ir).toEqual({
            kind: "list",
            text: " a ",
            children: [
                { kind: "#comment", text: " c ", tail: " b " },
                { kind: "field", attrs: { name: "x" }, tail: " d " },
                { kind: "#pi", attrs: { target: "pi" }, text: "e" },
            ],
        });
    });
});
