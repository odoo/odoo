import { isBlock } from "@html_editor/utils/blocks";
import {
    ancestors,
    closestElement,
    descendants,
    firstLeaf,
    getAdjacentNextSiblings,
    getAdjacentPreviousSiblings,
    getAdjacents,
    lastLeaf,
    getCommonAncestor,
} from "@html_editor/utils/dom_traversal";
import { describe, expect, getFixture, test } from "@odoo/hoot";
import { insertTestHtml } from "../_helpers/editor";
import { unformat } from "../_helpers/format";

describe("closestElement", () => {
    test("should find the closest element to a text node", () => {
        const [div] = insertTestHtml("<div><p>abc</p></div>");
        const p = div.firstChild;
        const abc = p.firstChild;
        const result = closestElement(abc);
        expect(result).toBe(p);
    });

    test("should find that the closest element to an element is itself", () => {
        const [p] = insertTestHtml("<p>abc</p>");
        const result = closestElement(p);
        expect(result).toBe(p);
    });

    test("should not find a node which is not contained inside a .odoo-editor-editable", () => {
        const [div] = insertTestHtml(`<div><p>abc</p></div>`);
        const p = div.querySelector("p");
        let result = closestElement(p, "div");
        expect(result).toBe(div);
        const fixture = getFixture();
        fixture.classList.remove("odoo-editor-editable");
        result = closestElement(p, "div");
        expect(result).toBe(null);
    });

    test("should find a disconnected node even if not contained inside a .odoo-editor-editable element", () => {
        const [div] = insertTestHtml(`<div><p>abc</p></div>`);
        const p = div.querySelector("p");
        div.remove();
        const result = closestElement(p, "div");
        expect(result).toBe(div);
    });
});

describe("ancestors", () => {
    test("should find all the ancestors of a text node", () => {
        const [div] = insertTestHtml(
            "<div><div><div><p>abc</p><div><p>def</p></div></div></div></div>"
        );
        const editable = div.parentElement;
        const abcAncestors = [
            editable,
            div,
            div.firstChild,
            div.firstChild.firstChild,
            div.firstChild.firstChild.firstChild,
        ].reverse();
        const abc = abcAncestors[0].firstChild;
        const result = ancestors(abc, editable);
        expect(result).toEqual(abcAncestors);
    });

    test("should find only the editable", () => {
        const [p] = insertTestHtml("<p>abc</p>");
        const editable = p.parentElement;
        const result = ancestors(p, editable);
        expect(result).toEqual([editable]);
    });
});

describe("descendants", () => {
    test("should find all the descendants of a div in depth-first order", () => {
        const [div] = insertTestHtml(
            "<div><div><div><p>abc</p><div><p>def</p></div></div></div></div>"
        );
        expect(descendants(div)).toEqual([
            div.firstChild, // <div><div>...
            div.firstChild.firstChild, // <div><div><div>...
            div.firstChild.firstChild.firstChild, // <p>abc</p>
            div.firstChild.firstChild.firstChild.firstChild, // "abc"
            div.firstChild.firstChild.childNodes[1], // <div><p>def</p></div>
            div.firstChild.firstChild.childNodes[1].firstChild, // <p>def</p>
            div.firstChild.firstChild.childNodes[1].firstChild.firstChild, // "def"
        ]);
    });
});

describe("lastLeaf", () => {
    test("should find the last leaf of a child-rich block", () => {
        const [div] = insertTestHtml(
            "<div><div><p>ab<span>cd</span><b><i><u>ef</u></i></b></p></div></div>"
        );
        const p = div.firstChild.firstChild;
        const ef = p.childNodes[2].firstChild.firstChild.firstChild;
        const result = lastLeaf(div);
        expect(result).toBe(ef);
    });

    test("should find that the last closest block descendant of a child-rich block is itself", () => {
        const [div] = insertTestHtml(
            "<div><div><p>ab<span>cd</span><b><i><u>ef</u></i></b></p></div></div>"
        );
        const result = lastLeaf(div, isBlock);
        expect(result).toBe(div);
    });

    test("should find no last closest block descendant of a child-rich inline and return its last leaf instead", () => {
        const [div] = insertTestHtml(
            "<div><div><p>ab<span>cd</span><b><i><u>ef</u></i></b></p></div></div>"
        );
        const b = div.firstChild.firstChild.childNodes[2];
        const ef = b.firstChild.firstChild.firstChild;
        const result = lastLeaf(b, isBlock);
        expect(result).toBe(ef);
    });
});

describe("firstLeaf", () => {
    test("should find the first leaf of a child-rich block", () => {
        const [div] = insertTestHtml(
            "<div><div><p><b><i><u>ab</u></i></b><span>cd</span>ef</p></div></div>"
        );
        const p = div.firstChild.firstChild;
        const ab = p.firstChild.firstChild.firstChild.firstChild;
        const result = firstLeaf(div);
        expect(result).toBe(ab);
    });

    test("should find that the first closest block descendant of a child-rich block is itself", () => {
        const [div] = insertTestHtml(
            "<div><div><p>ab<span>cd</span><b><i><u>ef</u></i></b></p></div></div>"
        );
        const result = firstLeaf(div, isBlock);
        expect(result).toBe(div);
    });

    test("should find no first closest block descendant of a child-rich inline and return its first leaf instead", () => {
        const [div] = insertTestHtml(
            "<div><div><p><b><i><u>ab</u></i></b><span>cd</span>ef</p></div></div>"
        );
        const b = div.firstChild.firstChild.firstChild;
        const ab = b.firstChild.firstChild.firstChild;
        const result = firstLeaf(b, isBlock);
        expect(result).toBe(ab);
    });
});

describe("getAdjacentPreviousSiblings", () => {
    test("should find the adjacent previous siblings of a deeply nested node", () => {
        const [p] = insertTestHtml("<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>");
        const gh = p.firstChild.childNodes[1].childNodes[2];
        const u = gh.previousSibling;
        const cd = u.previousSibling;
        const result = getAdjacentPreviousSiblings(gh);
        expect(result).toEqual([u, cd]);
    });

    test("should find no adjacent previous siblings of a deeply nested node", () => {
        const [p] = insertTestHtml("<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>");
        const ij = p.firstChild.childNodes[1].childNodes[3].firstChild;
        const result = getAdjacentPreviousSiblings(ij);
        expect(result).toEqual([]);
    });

    test("should find only the adjacent previous siblings of a deeply nested node that are elements", () => {
        const [p] = insertTestHtml("<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>");
        const gh = p.firstChild.childNodes[1].childNodes[2];
        const u = gh.previousSibling;
        const result = getAdjacentPreviousSiblings(
            gh,
            (node) => node.nodeType === Node.ELEMENT_NODE
        );
        expect(result).toEqual([u]);
    });

    test("should find only the adjacent previous siblings of a deeply nested node that are text nodes (none)", () => {
        const [p] = insertTestHtml("<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>");
        const gh = p.firstChild.childNodes[1].childNodes[2];
        const result = getAdjacentPreviousSiblings(gh, (node) => node.nodeType === Node.TEXT_NODE);
        expect(result).toEqual([]);
    });
});

describe("getAdjacentNextSiblings", () => {
    test("should find the adjacent next siblings of a deeply nested node", () => {
        const [p] = insertTestHtml("<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>");
        const gh = p.firstChild.childNodes[1].childNodes[2];
        const span = gh.nextSibling;
        const kl = span.nextSibling;
        const result = getAdjacentNextSiblings(gh);
        expect(result).toEqual([span, kl]);
    });

    test("should find no adjacent next siblings of a deeply nested node", () => {
        const [p] = insertTestHtml("<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>");
        const ij = p.firstChild.childNodes[1].childNodes[3].firstChild;
        const result = getAdjacentNextSiblings(ij);
        expect(result).toEqual([]);
    });

    test("should find only the adjacent next siblings of a deeply nested node that are elements", () => {
        const [p] = insertTestHtml("<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>");
        const gh = p.firstChild.childNodes[1].childNodes[2];
        const span = gh.nextSibling;
        const result = getAdjacentNextSiblings(gh, (node) => node.nodeType === Node.ELEMENT_NODE);
        expect(result).toEqual([span]);
    });

    test("should find only the adjacent next siblings of a deeply nested node that are text nodes (none)", () => {
        const [p] = insertTestHtml("<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>");
        const gh = p.firstChild.childNodes[1].childNodes[2];
        const result = getAdjacentNextSiblings(gh, (node) => node.nodeType === Node.TEXT_NODE);
        expect(result).toEqual([]);
    });
});

describe("getAdjacents", () => {
    test("should find the adjacent siblings of a deeply nested node", () => {
        const [p] = insertTestHtml("<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>");
        const gh = p.firstChild.childNodes[1].childNodes[2];
        const u = gh.previousSibling;
        const cd = u.previousSibling;
        const span = gh.nextSibling;
        const kl = span.nextSibling;
        const result = getAdjacents(gh);
        expect(result).toEqual([cd, u, gh, span, kl]);
    });

    test("should find no adjacent siblings of a deeply nested node", () => {
        const [p] = insertTestHtml("<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>");
        const ij = p.firstChild.childNodes[1].childNodes[3].firstChild;
        const result = getAdjacents(ij);
        expect(result).toEqual([ij]);
    });

    test("should find the adjacent siblings of a deeply nested node that are elements", () => {
        const [p] = insertTestHtml(
            "<p><b>ab<i>cd<u>ef</u><span>gh</span><span>ij</span>kl</i>mn</b>op</p>"
        );
        const gh = p.firstChild.childNodes[1].childNodes[2];
        const u = gh.previousSibling;
        const span = gh.nextSibling;
        const result = getAdjacents(gh, (node) => node.nodeType === Node.ELEMENT_NODE);
        expect(result).toEqual([u, gh, span]);
    });

    test("should return an empty array if the given node is not satisfying the given predicate", () => {
        const [p] = insertTestHtml(
            "<p><b>ab<i>cd<u>ef</u><a>gh</a>ij<span>kl</span>mn</i>op</b>qr</p>"
        );
        const a = p.querySelector("a");
        const result = getAdjacents(a, (node) => node.nodeType === Node.TEXT_NODE);
        expect(result).toEqual([]);
    });
});
describe("getCommonAncestor", () => {
    let root, p1, p2, span1, span2, ul, li1, li2, li3, li4, ol;
    const prepareHtml = () => {
        [root] = insertTestHtml(
            unformat(`
            <div>
                <p> paragraph 1 </p>
                <p>
                    paragraph 2
                    <span> span1 </span>
                    <span> span2 </span>
                <p/>
                <ul>
                    <li> list item 1 </li>
                    <li id="li2" class="oe-nested">
                        <ol>
                            <li> list item 3 </li>
                            <li> list item 4 </li>
                        </ol>
                    </li>
                </ul>
            </div>
        `)
        );
        [p1, p2] = root.querySelectorAll("p");
        [span1, span2] = root.querySelectorAll("span");
        [ul] = root.querySelectorAll("ul");
        [li1, li2, li3, li4] = root.querySelectorAll("li");
        [ol] = root.querySelectorAll("ol");
    };

    test("should return null if no nodes are provided", () => {
        prepareHtml();
        const result = getCommonAncestor([]);
        expect(result).toBe(null);
    });

    test("should return the node itself if only one node is provided", () => {
        prepareHtml();
        const result = getCommonAncestor([p1]);
        expect(result).toBe(p1);
    });

    test("should return the node itself if the same node is provided twice", () => {
        prepareHtml();
        const result = getCommonAncestor([p1, p1]);
        expect(result).toBe(p1);
    });

    test("should return null if there's no common ancestor within the root", () => {
        prepareHtml();
        let result = getCommonAncestor([span1, span2], p1);
        expect(result).toBe(null);

        result = getCommonAncestor([ol], li1);
        expect(result).toBe(null);
    });

    test("should return the common ancestor element of two nodes", () => {
        prepareHtml();
        let result = getCommonAncestor([span1, span2]);
        expect(result).toBe(p2);

        result = getCommonAncestor([li1, li3]);
        expect(result).toBe(ul);
    });

    test("should return the common ancestor element of multiple nodes", () => {
        prepareHtml();
        let result = getCommonAncestor([li1, li2, li3, li4], root);
        expect(result).toBe(ul);

        result = getCommonAncestor([p2, span1, span2], root);
        expect(result).toBe(p2);

        result = getCommonAncestor([span1, li1, ol], root);
        expect(result).toBe(root);
    });
});
