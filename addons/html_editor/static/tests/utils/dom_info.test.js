import { isVisible, isVisibleTextNode, nextLeaf, previousLeaf } from "@html_editor/utils/dom_info";
import { describe, expect, test } from "@odoo/hoot";
import { insertTestHtml } from "../_helpers/editor";

describe("previousLeaf", () => {
    test("should find the previous leaf of a deeply nested node", () => {
        const [div] = insertTestHtml(
            "<div><div><p><b>ab<i>cd<u>ef</u>gh</i></b><span>ij</span>kl</p></div></div>"
        );
        const editable = div.parentElement;
        const p = div.firstChild.firstChild;
        const gh = p.firstChild.childNodes[1].childNodes[2];
        const ij = p.childNodes[1].firstChild;
        const result = previousLeaf(ij, editable);
        expect(result).toBe(gh);
    });

    test("should find no previous leaf and return undefined", () => {
        const [div] = insertTestHtml(
            "<div><div><p><b>ab<i>cd<u>ef</u>gh</i></b><span>ij</span>kl</p></div></div>"
        );
        const editable = div.parentElement;
        const p = div.firstChild.firstChild;
        const ab = p.firstChild.firstChild;
        const result = previousLeaf(ab, editable);
        expect(result).toBe(undefined);
    });

    test("should find the previous leaf of a deeply nested node, skipping invisible nodes", () => {
        const [div] = insertTestHtml(
            `<div>
                <div>
                    <p>
                        <b>ab<i>cd<u>ef</u>gh</i></b>
                    </p>
                    <p>
                        <span>ij</span>kl
                    </p>
                </div>
            </div>`
        );
        const editable = div.parentElement;
        const p1 = div.childNodes[1].childNodes[1];
        const gh = p1.childNodes[1].childNodes[1].childNodes[2];
        const p2 = div.childNodes[1].childNodes[3];
        const ij = p2.childNodes[1].firstChild;
        const result = previousLeaf(ij, editable, true);
        expect(result).toBe(gh);
    });

    test("should find no previous leaf, skipping invisible nodes, and return undefined", () => {
        const [div] = insertTestHtml(
            `<div>
                <div>
                    <p>
                        <b>ab<i>cd<u>ef</u>gh</i></b>
                    </p>
                    <p>
                        <span>ij</span>kl
                    </p>
                </div>
            </div>`
        );
        const editable = div.parentElement;
        const p1 = div.childNodes[1].childNodes[1];
        const ab = p1.childNodes[1].firstChild;
        const result = previousLeaf(ab, editable, true);
        expect(result).toBe(undefined);
    });

    test("should find the previous leaf of a deeply nested node to be whitespace", () => {
        const [div] = insertTestHtml(
            `<div>
                <div>
                    <p>
                        <b>ab<i>cd<u>ef</u>gh</i></b>
                    </p>
                    <p>
                        <span>ij</span>kl
                    </p>
                </div>
            </div>`
        );
        const editable = div.parentElement;
        const p2 = div.childNodes[1].childNodes[3];
        const whitespace = p2.firstChild;
        const ij = p2.childNodes[1].firstChild;
        const result = previousLeaf(ij, editable);
        expect(result).toBe(whitespace);
        expect(whitespace.nodeType === Node.TEXT_NODE).toBe(true);
        expect(whitespace.textContent).toBe(`
                        `);
        expect(isVisibleTextNode(whitespace)).toBe(false);
    });
});

describe("nextLeaf", () => {
    // TODO @phoenix: add nextLeaf test cases when we add it in the code base
    test("should find the next leaf of a deeply nested node", () => {
        const [div] = insertTestHtml(
            "<div><div><p><b>ab<i>cd<u>ef</u>gh</i></b><span>ij</span>kl</p></div></div>"
        );
        const editable = div.parentElement;
        const p = div.firstChild.firstChild;
        const gh = p.firstChild.childNodes[1].childNodes[2];
        const ij = p.childNodes[1].firstChild;
        const result = nextLeaf(gh, editable);
        expect(result).toBe(ij);
    });

    test("should find no next leaf and return undefined", () => {
        const [div] = insertTestHtml(
            "<div><div><p><b>ab<i>cd<u>ef</u>gh</i></b><span>ij</span>kl</p></div></div>"
        );
        const editable = div.parentElement;
        const p = div.firstChild.firstChild;
        const kl = p.childNodes[2];
        const result = nextLeaf(kl, editable);
        expect(result).toBe(undefined);
    });

    test("should find the next leaf of a deeply nested node, skipping invisible nodes", () => {
        const [div] = insertTestHtml(
            `<div>
                <div>
                    <p>
                        <b>ab<i>cd<u>ef</u>gh</i></b>
                    </p>
                    <p>
                        <span>ij</span>kl
                    </p>
                </div>
            </div>`
        );
        const editable = div.parentElement;
        const p1 = div.childNodes[1].childNodes[1];
        const gh = p1.childNodes[1].childNodes[1].childNodes[2];
        const p2 = div.childNodes[1].childNodes[3];
        const ij = p2.childNodes[1].firstChild;
        const result = nextLeaf(gh, editable, true);
        expect(result).toBe(ij);
    });

    test("should find no next leaf, skipping invisible nodes, and return undefined", () => {
        const [div] = insertTestHtml(
            `<div>
                <div>
                    <p>
                        <b>ab<i>cd<u>ef</u>gh</i></b>
                    </p>
                    <p>
                        <span>ij</span>kl
                    </p>
                </div>
            </div>`
        );
        const editable = div.parentElement;
        const p2 = div.childNodes[1].childNodes[3];
        const kl = p2.childNodes[2];
        const result = nextLeaf(kl, editable, true);
        expect(result).toBe(undefined);
    });

    test("should find the next leaf of a deeply nested node to be whitespace", () => {
        const [div] = insertTestHtml(
            `<div>
                <div>
                    <p>
                        <b>ab<i>cd<u>ef</u>gh</i></b>
                    </p>
                    <p>
                        <span>ij</span>kl
                    </p>
                </div>
            </div>`
        );
        const editable = div.parentElement;
        const p2 = div.childNodes[1].childNodes[3];
        const kl = p2.childNodes[2];
        const whitespace = div.childNodes[1].childNodes[4];
        const result = nextLeaf(kl, editable);
        expect(result).toBe(whitespace);
        expect(whitespace.nodeType === Node.TEXT_NODE).toBe(true);
        expect(whitespace.textContent).toBe(`
                `);
        expect(isVisibleTextNode(whitespace)).toBe(false);
    });
});

describe("isVisible", () => {
    describe("textNode", () => {
        test("should identify an invisible textnode at the beginning of a paragraph before an inline node", () => {
            const [p] = insertTestHtml("<p> <i>a</i></p>");
            const result = isVisible(p.firstChild);
            expect(result).not.toBe(true);
        });

        test("should identify invisible string space at the end of a paragraph after an inline node", () => {
            const [p] = insertTestHtml("<p><i>a</i> </p>");
            const result = isVisible(p.lastChild);
            expect(result).not.toBe(true);
        });

        test("should identify a single visible space in an inline node in the middle of a paragraph", () => {
            const [p] = insertTestHtml("<p>a<i> </i>b</p>");
            const result = isVisible(p.querySelector("i").firstChild);
            expect(result).toBe(true);
        });

        test("should identify a visible string with only one visible space in an inline node in the middle of a paragraph", () => {
            const [p] = insertTestHtml("<p>a<i>   </i>b</p>");
            const result = isVisible(p.querySelector("i").firstChild);
            expect(result).toBe(true);
        });

        test("should identify a visible space in the middle of a paragraph", () => {
            const [p] = insertTestHtml("<p></p>");
            // insert 'a b' as three separate text node inside p
            const textNodes = "a b".split("").map((char) => {
                const textNode = document.createTextNode(char);
                p.appendChild(textNode);
                return textNode;
            });
            const result = isVisible(textNodes[1]);
            expect(result).toBe(true);
        });

        test("should identify a visible string space in the middle of a paragraph", () => {
            const [p] = insertTestHtml("<p></p>");
            // inserts 'a', '   ' and  'b' as 3 separate text nodes inside p
            const textNodes = ["a", "   ", "b"].map((char) => {
                const textNode = document.createTextNode(char);
                p.appendChild(textNode);
                return textNode;
            });
            const result = isVisible(textNodes[1]);
            expect(result).toBe(true);
        });

        test("should identify the first space in a series of spaces as in the middle of a paragraph as visible", () => {
            const [p] = insertTestHtml("<p></p>");
            // inserts 'a   b' as 5 separate text nodes inside p
            const textNodes = "a   b".split("").map((char) => {
                const textNode = document.createTextNode(char);
                p.appendChild(textNode);
                return textNode;
            });
            const result = isVisible(textNodes[1]);
            expect(result).toBe(true);
        });

        test("should identify the second space in a series of spaces in the middle of a paragraph as invisible", () => {
            const [p] = insertTestHtml("<p></p>");
            // inserts 'a   b' as 5 separate text nodes inside p
            const textNodes = "a   b".split("").map((char) => {
                const textNode = document.createTextNode(char);
                p.appendChild(textNode);
                return textNode;
            });
            const result = isVisible(textNodes[2]);
            expect(result).not.toBe(true);
        });

        test("should identify empty text node as invisible", () => {
            const [p] = insertTestHtml("<p></p>");
            // inserts 'a   b' as 5 separate text nodes inside p
            const textNode = document.createTextNode("");
            p.appendChild(textNode);
            const result = isVisible(textNode);
            expect(result).not.toBe(true);
        });

        test("should identify a space between to visible char in inline nodes as visible", () => {
            const [p] = insertTestHtml("<p><i>a</i> <i>b</i></p>");
            const textNode = p.firstChild.nextSibling;

            const result = isVisible(textNode);

            expect(result).toBe(true);
        });
    });
});
