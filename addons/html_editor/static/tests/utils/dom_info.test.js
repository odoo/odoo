import {
    areSimilarElements,
    getDeepestPosition,
    isEmptyBlock,
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

    test("should identify a div contains button without text content as non-empty", () => {
        const [div] = insertTestHtml("<div><button></button></div>");
        const result = isEmptyBlock(div);
        expect(result).toBe(false);
    });
});

describe("isShrunkBlock", () => {
    test("should not consider a HR as a shrunk block", () => {
        const [hr] = insertTestHtml("<hr>");
        const result = isShrunkBlock(hr);
        expect(result).toBe(false);
    });
    test("should not consider a block containing a canvas as a shrunk block", () => {
        const [canvas] = insertTestHtml("<canvas></canvas>");
        const result = isShrunkBlock(canvas);
        expect(result).toBe(false);
    });
});

describe("areSimilarElements", () => {
    test("should consider elements with same classes and styles in different orders as similar", () => {
        const [span1, span2] = insertTestHtml(
            "<span class='first second' style='color: red; color2: blue'>hello</span><span class='second first' style='color2: blue; color: red'>world</span>"
        );
        const result = areSimilarElements(span1, span2);
        expect(result).toBe(true);
    });
    test("return false when the number of styles are different", () => {
        const [span1, span2] = insertTestHtml(
            "<span class='first second' style='color: red; color2: blue'>hello</span><span class='second first' style='color2: blue;'>world</span>"
        );
        const result = areSimilarElements(span1, span2);
        expect(result).toBe(false);
    });
    test("return false when the number of classes are different", () => {
        const [span1, span2] = insertTestHtml(
            "<span class='first' style='color: red; color2: blue'>hello</span><span class='second first' style='color2: blue;'>world</span>"
        );
        const result = areSimilarElements(span1, span2);
        expect(result).toBe(false);
    });
    test("return false when classes are different", () => {
        const [span1, span2] = insertTestHtml(
            "<span class='first' style='color: red; color2: blue'>hello</span><span class='second' style='color2: blue;'>world</span>"
        );
        const result = areSimilarElements(span1, span2);
        expect(result).toBe(false);
    });
    test("return false when styles are different", () => {
        const [span1, span2] = insertTestHtml(
            "<span class='first second' style='color2: blue'>hello</span><span class='second first' style='color2: blue; color: red'>world</span>"
        );
        const result = areSimilarElements(span1, span2);
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
