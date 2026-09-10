import {
    getCachedStyleProperty,
    getDeepestPosition,
    isEmptyBlock,
    isRedundantElement,
    isShrunkBlock,
    isVisible,
    isVisibleTextNode,
    nextLeaf,
    previousLeaf,
} from "@html_editor/utils/dom_info";
import { describe, expect, test } from "@odoo/hoot";
import { insertTestHtml } from "../_helpers/editor";
import { isBlock } from "../../src/utils/blocks";

const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

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
        expect(whitespace.nodeType).toBe(Node.TEXT_NODE);
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
        expect(whitespace.nodeType).toBe(Node.TEXT_NODE);
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

describe("getDeepestPosition", () => {
    test("should get deepest position for text within paragraph", () => {
        const [p] = insertTestHtml("<p>abc</p>");
        const editable = p.parentElement;
        const abc = p.firstChild;
        let [node, offset] = getDeepestPosition(editable, 0);
        expect([node, offset]).toEqual([abc, 0]);
        [node, offset] = getDeepestPosition(editable, 1);
        expect([node, offset]).toEqual([abc, 3]);
    });
    test("should get deepest position within nested formatting tags", () => {
        const [p] = insertTestHtml("<p><span><b><i><u>abc</u></i></b></span></p>");
        const editable = p.parentElement;
        const abc = p.firstChild.firstChild.firstChild.firstChild.firstChild;
        let [node, offset] = getDeepestPosition(editable, 0);
        expect([node, offset]).toEqual([abc, 0]);
        [node, offset] = getDeepestPosition(editable, 1);
        expect([node, offset]).toEqual([abc, 3]);
    });
    test("should get deepest position in multiple paragraph", () => {
        const [p1, p2] = insertTestHtml("<p>abc</p><p>def</p>");
        const editable = p1.parentElement;
        const abc = p1.firstChild;
        const def = p2.firstChild;
        let [node, offset] = getDeepestPosition(editable, 0);
        expect([node, offset]).toEqual([abc, 0]);
        [node, offset] = getDeepestPosition(editable, 1);
        expect([node, offset]).toEqual([def, 0]);
        [node, offset] = getDeepestPosition(editable, 2);
        expect([node, offset]).toEqual([def, 3]);
    });
    test("should get deepest position for node with invisible element", () => {
        const [p1] = insertTestHtml("<p></p><p>def</p>");
        const editable = p1.parentElement;
        const def = editable.lastChild.firstChild;
        let [node, offset] = getDeepestPosition(editable, 0);
        expect([node, offset]).toEqual([def, 0]);
        [node, offset] = getDeepestPosition(editable, 2);
        expect([node, offset]).toEqual([def, 3]);
    });
    test("should get deepest position for invisible block element", () => {
        const [p1] = insertTestHtml("<p></p><p>def</p>");
        const [node, offset] = getDeepestPosition(p1, 0);
        expect([node, offset]).toEqual([p1, 0]);
    });
    test("should get deepest position for invisible block element(2)", () => {
        const [p1] = insertTestHtml("<p>abc</p><p></p>");
        const p2 = p1.nextSibling;
        const [node, offset] = getDeepestPosition(p2, 0);
        expect([node, offset]).toEqual([p2, 0]);
    });
    test("should get deepest position for elements containing invisible text nodes", () => {
        const [p] = insertTestHtml(
            `<p>
                <i>a</i>
            </p>`
        );
        const editable = p.parentElement;
        const a = editable.firstChild.childNodes[1].firstChild;
        let [node, offset] = getDeepestPosition(editable, 0);
        expect([node, offset]).toEqual([a, 0]);
        [node, offset] = getDeepestPosition(editable, 1);
        expect([node, offset]).toEqual([a, 1]);
    });
    test("should not skip zwnbsp", () => {
        const [a] = insertTestHtml('\ufeff<a href="#">abc</a>');
        const editable = a.parentElement;
        const zwnbsp = editable.firstChild;
        const [node, offset] = getDeepestPosition(editable, 0);
        expect([node, offset]).toEqual([zwnbsp, 0]);
    });
});

describe("isEmptyBlock", () => {
    test("should identify empty p element", () => {
        const [p] = insertTestHtml("<p></p>");
        const result = isEmptyBlock(p);
        expect(result).toBe(true);
    });

    test("should identify p with single br tag as empty and multiple br tag as non-empty", () => {
        const [p1, p2] = insertTestHtml("<p><br></p><p><br><br></p>");
        const result1 = isEmptyBlock(p1);
        const result2 = isEmptyBlock(p2);
        expect(result1).toBe(true);
        expect(result2).toBe(false);
    });

    test("should identify p element with text content as non-empty", () => {
        const [p] = insertTestHtml("<p>abc</p>");
        const result1 = isEmptyBlock(p);
        const result2 = isEmptyBlock(p.firstChild);
        expect(result1).toBe(false);
        expect(result2).toBe(false);
    });

    test("should identify a empty span with display block", () => {
        const [span] = insertTestHtml('<span style="display: block;"><br></span>');
        const result = isEmptyBlock(span);
        expect(result).toBe(true);
    });

    test("should identify span with icon classes as non-empty", () => {
        const [span] = insertTestHtml('<span class="fa fa-trash-o"></span>');
        const result = isEmptyBlock(span);
        expect(result).toBe(false);
    });

    test("should identify img element as non-empty", () => {
        const [img] = insertTestHtml(`<img src="${base64Img}" alt="image">`);
        const result = isEmptyBlock(img);
        expect(result).toBe(false);
    });

    test("should identify empty a tag as non-empty", () => {
        const [a] = insertTestHtml("<a></a>");
        const result = isEmptyBlock(a);
        expect(result).toBe(false);
    });

    test("should identify a tag with text as non-empty", () => {
        const [a] = insertTestHtml('<a href="#">Link text</a>');
        const result = isEmptyBlock(a);
        expect(result).toBe(false);
    });

    test("should return false for a p containing media element", () => {
        const [p] = insertTestHtml(
            '<p><a href="#" title="document" data-mimetype="application/pdf" class="o_image" contenteditable="false"></a></p>'
        );
        const result = isEmptyBlock(p);
        expect(result).toBe(false);
    });
});

describe("isShrunkBlock", () => {
    test("should not consider a HR as a shrunk block", () => {
        const [hr] = insertTestHtml("<hr>");
        const result = isShrunkBlock(hr);
        expect(result).toBe(false);
    });
});

describe("isBlock on display none elements", () => {
    test("t element should not be block", () => {
        const [t] = insertTestHtml(`<t style="display: none"></t>`);
        const result = isBlock(t);
        expect(result).toBe(false);
    });
    test("span element should not be block", () => {
        const [span] = insertTestHtml(`<span style="display: none"></span>`);
        const result = isBlock(span);
        expect(result).toBe(false);
    });
});

describe("getCachedStyleProperty", () => {
    test("should return correct computed style value for element node", () => {
        const [spanElement] = insertTestHtml(`<span style="color: red;">text</span>`);
        const computedColor = getCachedStyleProperty(spanElement, "color");
        expect(computedColor).toBe("rgb(255, 0, 0)");
    });

    test("should update cached computed style property when inline style is mutated", () => {
        const [spanElement] = insertTestHtml(`<span style="color: red;">text</span>`);

        const initialColor = getCachedStyleProperty(spanElement, "color");
        expect(initialColor).toBe("rgb(255, 0, 0)");

        spanElement.style.color = "blue";

        const liveColor = getComputedStyle(spanElement).color;
        const updatedColor = getCachedStyleProperty(spanElement, "color");

        expect(updatedColor).toBe(liveColor);
        expect(updatedColor).toBe("rgb(0, 0, 255)");
    });

    test("should reflect updated computed style on child element when parent element style is mutated", () => {
        const [parentElement] = insertTestHtml(
            `<div style="color: blue;"><span style="color: green;">child text</span></div>`
        );
        const childElement = parentElement.firstChild;

        const initialChildColor = getCachedStyleProperty(childElement, "color");
        const initialParentColor = getCachedStyleProperty(parentElement, "color");
        expect(initialChildColor).toBe("rgb(0, 128, 0)");
        expect(initialParentColor).toBe("rgb(0, 0, 255)");

        parentElement.style.color = "green";

        const updatedParentColor = getCachedStyleProperty(parentElement, "color");
        expect(updatedParentColor).toBe("rgb(0, 128, 0)");
    });

    test("should support both camelCase and kebab-case style property names", () => {
        const [spanElement] = insertTestHtml(
            `<span style="font-size: 16px; text-decoration-line: underline;">text</span>`
        );
        const camelCaseFontSize = getCachedStyleProperty(spanElement, "fontSize");
        const kebabCaseFontSize = getCachedStyleProperty(spanElement, "font-size");
        const textDecorationLine = getCachedStyleProperty(spanElement, "text-decoration-line");

        expect(camelCaseFontSize).toBe("16px");
        expect(kebabCaseFontSize).toBe("16px");
        expect(textDecorationLine).toBe("underline");
    });
});

describe("isRedundantElement", () => {
    test("should return false for nodes inside QWeb directive elements or with QWeb attributes", () => {
        const [tElement] = insertTestHtml(`<t t-out="foo"><b>text</b></t>`);
        const innerB = tElement.firstChild;
        expect(isRedundantElement(innerB)).toBe(false);

        const [pElement] = insertTestHtml(`<p t-field="bar"><b>text</b></p>`);
        const bInP = pElement.firstChild;
        expect(isRedundantElement(bInP)).toBe(false);
    });

    test("should detect semantic formatting tags as redundant when parent already has that visual formatting", () => {
        const [pElement] = insertTestHtml(
            `<p style="font-weight: bold;"><b>boldText</b><i>italicText</i><u>underlineText</u></p>`
        );
        const b = pElement.childNodes[0];
        const i = pElement.childNodes[1];
        const u = pElement.childNodes[2];

        expect(isRedundantElement(b)).toBe(true);
        expect(isRedundantElement(i)).toBe(false);
        expect(isRedundantElement(u)).toBe(false);
    });

    test("should unwrap nested small tags", () => {
        const [pElement] = insertTestHtml(`<p><small><small>small text</small></small></p>`);
        const outerSmall = pElement.firstChild;
        const innerSmall = outerSmall.firstChild;

        expect(isRedundantElement(outerSmall)).toBe(false);
        expect(isRedundantElement(innerSmall)).toBe(true);
    });

    test("should detect strong tag inside a visually-bold parent via class as redundant", () => {
        const [, pElement] = insertTestHtml(
            `<style>.boldClass { font-weight: bold; }</style><p class="boldClass"><strong>bold text</strong></p>`
        );
        const strong = pElement.firstChild;

        expect(isRedundantElement(strong)).toBe(true);
    });

    test("should evaluate empty span/font (0 attributes) as redundant only when parent is exact same tag", () => {
        const [p1] = insertTestHtml(`<span><span>nested span</span></span>`);
        const innerSpan = p1.firstChild;
        expect(isRedundantElement(innerSpan)).toBe(true);

        const [p2] = insertTestHtml(`<font><span>nested different tag</span></font>`);
        const innerSpanInFont = p2.firstChild;
        expect(isRedundantElement(innerSpanInFont)).toBe(false);
    });

    test("should return false for span/font containing exotic attributes like id, data-*, lang", () => {
        const [pElement] = insertTestHtml(
            `<p style="color: red;"><span style="color: red;" id="my-span" data-test="123" lang="en">text</span></p>`
        );
        const span = pElement.firstChild;

        expect(isRedundantElement(span)).toBe(false);
    });

    test("should detect inline style matching parent computed style as redundant", () => {
        const [parentElement] = insertTestHtml(
            `<div style="color: rgb(255, 0, 0);"><span style="color: red;">text</span></div>`
        );
        const span = parentElement.firstChild;

        expect(isRedundantElement(span)).toBe(true);
    });

    test("should reject redundancy for intermediate style overrides", () => {
        const [outerFont] = insertTestHtml(
            `<font style="color: red;"><span style="color: blue;"><font style="color: red;">text</font></span></font>`
        );
        const middleSpan = outerFont.firstChild;
        const innerFont = middleSpan.firstChild;

        expect(isRedundantElement(middleSpan)).toBe(false);
        expect(isRedundantElement(innerFont)).toBe(false);
    });

    test("should detect color class already covered by ancestor span or font as redundant", () => {
        const [outerSpan] = insertTestHtml(
            `<span class="text-danger"><span class="text-danger">danger text</span></span>`
        );
        const innerSpan = outerSpan.firstChild;

        expect(isRedundantElement(innerSpan)).toBe(true);
    });

    test("should reject redundancy when color class is overridden by a different class of same category on intermediate ancestor", () => {
        const [outerSpan] = insertTestHtml(
            `<span class="text-danger"><span class="text-primary"><span class="text-danger">text</span></span></span>`
        );
        const middleSpan = outerSpan.firstChild;
        const innerSpan = middleSpan.firstChild;

        expect(isRedundantElement(middleSpan)).toBe(false);
        expect(isRedundantElement(innerSpan)).toBe(false);
    });

    test("should return false when node classes are not all recognized color classes", () => {
        const [outerSpan] = insertTestHtml(
            `<span class="text-danger"><span class="text-danger my-custom-class">text</span></span>`
        );
        const innerSpan = outerSpan.firstChild;

        expect(isRedundantElement(innerSpan)).toBe(false);
    });

    test("should require both inline styles and color classes to be redundant when both are present", () => {
        const [outerSpan] = insertTestHtml(
            `<span style="color: red;" class="text-danger"><span style="color: red;" class="text-primary">text</span></span>`
        );
        const innerSpan = outerSpan.firstChild;

        expect(isRedundantElement(innerSpan)).toBe(false);
    });
});
