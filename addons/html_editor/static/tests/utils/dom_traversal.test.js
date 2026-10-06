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
    traverseNode,
    getNodesInRange,
} from "@html_editor/utils/dom_traversal";
import { describe, expect, getFixture, test } from "@odoo/hoot";
import { insertTestHtml } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { isElement, isTextNode, isVisible, isVisibleTextNode } from "@html_editor/utils/dom_info";

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
        const result = lastLeaf(div, { stopTraverseFunction: isBlock });
        expect(result).toBe(div);
    });

    test("should find no last closest block descendant of a child-rich inline and return its last leaf instead", () => {
        const [div] = insertTestHtml(
            "<div><div><p>ab<span>cd</span><b><i><u>ef</u></i></b></p></div></div>"
        );
        const b = div.firstChild.firstChild.childNodes[2];
        const ef = b.firstChild.firstChild.firstChild;
        const result = lastLeaf(b, { stopTraverseFunction: isBlock });
        expect(result).toBe(ef);
    });

    test("should find the deepest visible node", () => {
        const [div] = insertTestHtml(
            "<div><p><span>a</span>b<span><span>c</span>d<span><span>\uFEFF</span>\uFEFF</span>\uFEFF</span>\uFEFF</p>\uFEFF</div>"
        );
        const result = lastLeaf(div, { predicate: isVisible });
        expect(result.nodeType).toBe(Node.TEXT_NODE);
        expect(result.textContent).toBe("d");
    });

    test("should not return a skipped node", () => {
        const [div] = insertTestHtml("<div><p><span>\uFEFF</span></p></div>");
        const result = lastLeaf(div, {
            predicate: (node) => !(isTextNode(node) && !isVisibleTextNode(node)),
        });
        expect(result).toBe(div.querySelector("span"));
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
        const result = firstLeaf(div, { stopTraverseFunction: isBlock });
        expect(result).toBe(div);
    });

    test("should find no first closest block descendant of a child-rich inline and return its first leaf instead", () => {
        const [div] = insertTestHtml(
            "<div><div><p><b><i><u>ab</u></i></b><span>cd</span>ef</p></div></div>"
        );
        const b = div.firstChild.firstChild.firstChild;
        const ab = b.firstChild.firstChild.firstChild;
        const result = firstLeaf(b, { stopTraverseFunction: isBlock });
        expect(result).toBe(ab);
    });

    test("should find the deepest first node that isn't the letter 'a'", () => {
        const [div] = insertTestHtml(
            "<div>\uFEFF<p>\uFEFF<span>\uFEFF<span>b</span></span>c<span><span>d</span>e<span><span>f</span></span></span></p></div>"
        );
        const result = firstLeaf(div, { predicate: isVisible });
        expect(result.nodeType).toBe(Node.TEXT_NODE);
        expect(result.textContent).toBe("b");
    });

    test("should not return a skipped node", () => {
        const [div] = insertTestHtml("<div><p><span>\uFEFF</span></p></div>");
        const result = firstLeaf(div, {
            predicate: (node) => !(isTextNode(node) && !isVisibleTextNode(node)),
        });
        expect(result).toBe(div.querySelector("span"));
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
    let root, p1, p2, p3, span1, span2, li1, li2, li3, ol;
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
                    <li><p> list item 1 </p>
                        <ol>
                            <li> list item 2 </li>
                            <li> list item 3 </li>
                        </ol>
                    </li>
                </ul>
            </div>
        `)
        );
        [p1, p2, p3] = root.querySelectorAll("p");
        [span1, span2] = root.querySelectorAll("span");
        [li1, li2, li3] = root.querySelectorAll("li");
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

        result = getCommonAncestor([ol], p3);
        expect(result).toBe(null);
    });

    test("should return the common ancestor element of two nodes", () => {
        prepareHtml();
        let result = getCommonAncestor([span1, span2]);
        expect(result).toBe(p2);

        result = getCommonAncestor([li2, li3]);
        expect(result).toBe(ol);
    });

    test("should return the common ancestor element of multiple nodes", () => {
        prepareHtml();
        let result = getCommonAncestor([li1, li2, li3], root);
        expect(result).toBe(li1);

        result = getCommonAncestor([p2, span1, span2], root);
        expect(result).toBe(p2);

        result = getCommonAncestor([span1, li1, ol], root);
        expect(result).toBe(root);
    });
});

describe("traverseNode", () => {
    test("should iterate over non-skipped children", () => {
        const [root] = insertTestHtml(
            unformat(`
            <div id="a">
                <div id="b" class="skip">
                    <div id="c"></div>
                    <div id="d"></div>
                </div>
                <div id="e">
                    <div id="f"></div>
                    <div id="g" class="skip">
                        <div id="h"></div>
                        <div id="i"></div>
                    </div>
                    <div id="j"></div>
                </div>
            </div>
        `)
        );

        expect.verifySteps([]);
        traverseNode(root, (node) => {
            expect.step(node.id);
            return !node.classList.contains("skip");
        });
        expect.verifySteps(["a", "b", "e", "f", "g", "j"]);
    });
});

describe("getNodesInRange", () => {
    describe("basic", () => {
        describe("unfiltered", () => {
            test("should return the nodes between two blocks", () => {
                const [p1, p2, p3] = insertTestHtml(`<p>a</p><p>b</p><p>c</p>`);
                const nodes = getNodesInRange([p1, p3]);
                expect(nodes).toEqual([p1, p1.firstChild, p2, p2.firstChild, p3]);
            });
            test("should return the nodes between two empty blocks", () => {
                const [p1, p2, p3] = insertTestHtml(`<p><br></p><p><br></p><p><br></p>`);
                const nodes = getNodesInRange([p1, p3]);
                expect(nodes).toEqual([p1, p1.firstChild, p2, p2.firstChild, p3]);
            });
            test("should return the nodes between two text nodes in different blocks", () => {
                const [p1, p2, p3] = insertTestHtml(`<p>a</p><p>b</p><p>c</p>`);
                // From "a" to p3:
                const nodes = getNodesInRange([p1.firstChild, p3.firstChild]);
                expect(nodes).toEqual([p1.firstChild, p2, p2.firstChild, p3, p3.firstChild]);
            });
            test("should return the nodes between two text nodes in different blocks, with text node siblings", () => {
                const [p1, p2, p3] = insertTestHtml(`<p>a</p><p>c</p><p>d</p>`);
                const b = p1.ownerDocument.createTextNode("b");
                const e = p1.ownerDocument.createTextNode("e");
                p1.append(b); // <p>"a""b"</p>
                p3.append(e); // <p>"d""e"</p>
                // From "b" to "d" in `<p>ab</p><p>c</p><p>de</p>`:
                const nodes = getNodesInRange([b, p3.firstChild]);
                expect(nodes).toEqual([b, p2, p2.firstChild, p3, p3.firstChild]);
            });
            test("should return the nodes between a text node and a different block", () => {
                const [p1, p2, p3] = insertTestHtml(`<p>a</p><p>b</p><p>c</p>`);
                // From "a" to p3:
                const nodes = getNodesInRange([p1.firstChild, p3]);
                expect(nodes).toEqual([p1.firstChild, p2, p2.firstChild, p3]);
            });
            test("should return the start node when the range is collapsed", () => {
                const [, p2] = insertTestHtml(`<p>a</p><p>b</p><p>c</p>`);
                const nodes = getNodesInRange([p2, p2]);
                expect(nodes).toEqual([p2]);
            });
            test("should reverse the range if it's backwards", () => {
                const [p1, p2] = insertTestHtml(`<p>a</p><p>b</p><p>c</p>`);
                const nodes = getNodesInRange([p2, p1]);
                expect(nodes).toEqual([p1, p1.firstChild, p2]);
            });
        });
        describe("filtered", () => {
            describe("whatToShow", () => {
                test("should return only text nodes", () => {
                    const [p1, p2, p3] = insertTestHtml(`<p>a</p><p>c</p><p>d</p>`);
                    const b = p1.ownerDocument.createTextNode("b");
                    const e = p1.ownerDocument.createTextNode("e");
                    p1.append(b); // <p>"a""b"</p>
                    p3.append(e); // <p>"d""e"</p>
                    // From "b" to "d" in `<p>ab</p><p>c</p><p>de</p>`:
                    const nodes = getNodesInRange([b, p3.firstChild], {
                        whatToShow: NodeFilter.SHOW_TEXT,
                    });
                    expect(nodes).toEqual([b, p2.firstChild, p3.firstChild]);
                });
                test("should return only elements nodes", () => {
                    const [, p2, p3] = insertTestHtml(`<p>a</p><p>b</p><p>c</p>`);
                    const nodes = getNodesInRange([p2, p3], {
                        whatToShow: NodeFilter.SHOW_ELEMENT,
                    });
                    expect(nodes).toEqual([p2, p3]);
                });
                test("should return everything", () => {
                    const [p1, p2, p3] = insertTestHtml(`<p>a</p><p>c</p><p>d</p>`);
                    const b = p1.ownerDocument.createTextNode("b");
                    const e = p1.ownerDocument.createTextNode("e");
                    p1.append(b); // <p>"a""b"</p>
                    p3.append(e); // <p>"d""e"</p>
                    // From "b" to "d" in `<p>ab</p><p>c</p><p>de</p>`:
                    const nodes = getNodesInRange([b, p3.firstChild], {
                        whatToShow: NodeFilter.SHOW_ALL,
                    });
                    expect(nodes).toEqual([b, p2, p2.firstChild, p3, p3.firstChild]);
                });
                test("should not return the start node if it doesn't match whatToShow", () => {
                    const [p1, p2, p3] = insertTestHtml(`<p>a</p><p>b</p><p>c</p>`);
                    const d = p1.ownerDocument.createTextNode("d");
                    p3.append(d); // <p>"c""d"</p>
                    // From p2 to "c" in `<p>a</p><p>b</p><p>cd</p>`:
                    const nodes = getNodesInRange([p2, p3.firstChild], {
                        whatToShow: NodeFilter.SHOW_TEXT,
                    });
                    expect(nodes).toEqual([p2.firstChild, p3.firstChild]);
                });
                test("should not return the end node if it doesn't match whatToShow", () => {
                    const [p1, p2] = insertTestHtml(`<p>a</p><p>b</p><p>c</p>`);
                    const nodes = getNodesInRange([p1, p2], { whatToShow: NodeFilter.SHOW_TEXT });
                    expect(nodes).toEqual([p1.firstChild]);
                });
                test("should return nothing", () => {
                    const [p1, , p3] = insertTestHtml(`<p><br></p><p><br></p><p><br></p>`);
                    // From p1 to p3 > br:
                    const nodes = getNodesInRange([p1, p3.firstChild], {
                        whatToShow: NodeFilter.SHOW_TEXT,
                    });
                    expect(nodes).toEqual([]);
                });
            });
            const filterTests = [
                {
                    name: "should return only paragraphs and text nodes (filter skip)",
                    content: (filter) => () => {
                        const [h1, p, h2] = insertTestHtml(`<h1>a</h1><p>b</p><h2>c</h2>`);
                        // From h1 to "c":
                        const nodes = getNodesInRange([h1, h2.firstChild], { filter });
                        expect(nodes).toEqual([h1.firstChild, p, p.firstChild, h2.firstChild]);
                    },
                    filter: (node) =>
                        isTextNode(node) || node.nodeName === "P"
                            ? NodeFilter.FILTER_ACCEPT
                            : NodeFilter.FILTER_SKIP,
                },
                {
                    name: "should return only paragraphs and their text children (filter reject)",
                    content: (filter) => () => {
                        const [p1, , p2] = insertTestHtml(`<p>a</p><h1>b</h1><p>c</p>`);
                        // From p1 to "c":
                        const nodes = getNodesInRange([p1, p2.firstChild], { filter });
                        expect(nodes).toEqual([p1, p1.firstChild, p2, p2.firstChild]);
                    },
                    filter: (node) =>
                        isTextNode(node) || node.nodeName === "P"
                            ? NodeFilter.FILTER_ACCEPT
                            : NodeFilter.FILTER_REJECT,
                },
                {
                    name: "should not return the start node if it doesn't match the filter (filter skip)",
                    content: (filter) => () => {
                        const [h1, p, h2] = insertTestHtml(`<h1>a</h1><p>b</p><h2>c</h2>`);
                        // From h1 to "c":
                        const nodes = getNodesInRange([h1, h2.firstChild], { filter });
                        expect(nodes).toEqual([h1.firstChild, p, p.firstChild, h2, h2.firstChild]);
                    },
                    filter: (node) =>
                        node.nodeName === "H1" ? NodeFilter.FILTER_SKIP : NodeFilter.FILTER_ACCEPT,
                },
                {
                    name: "should not return the end node if it doesn't match the filter (filter skip)",
                    content: (filter) => () => {
                        const [h1, p, h2] = insertTestHtml(`<h1>a</h1><p>b</p><h2>c</h2>`);
                        const nodes = getNodesInRange([h1, h2], { filter });
                        expect(nodes).toEqual([h1, h1.firstChild, p, p.firstChild]);
                    },
                    filter: (node) =>
                        node.nodeName === "H2" ? NodeFilter.FILTER_SKIP : NodeFilter.FILTER_ACCEPT,
                },
                {
                    name: "should not return the start node's children if start rejects the filter (filter reject)",
                    content: (filter) => () => {
                        const [h1, p, h2] = insertTestHtml(`<h1>a</h1><p>b</p><h2>c</h2>`);
                        // From h1 to "c":
                        const nodes = getNodesInRange([h1, h2.firstChild], { filter });
                        expect(nodes).toEqual([p, p.firstChild, h2, h2.firstChild]);
                    },
                    filter: (node) =>
                        node.nodeName === "H1"
                            ? NodeFilter.FILTER_REJECT
                            : NodeFilter.FILTER_ACCEPT,
                },
                {
                    name: "should return nothing (filter skip)",
                    content: (filter) => () => {
                        const [h1, , h2] = insertTestHtml(`<h1>a</h1><p>b</p><h2>c</h2>`);
                        // From h1 to "c":
                        const nodes = getNodesInRange([h1, h2.firstChild], { filter });
                        expect(nodes).toEqual([]);
                    },
                    filter: () => NodeFilter.FILTER_SKIP,
                },
                {
                    name: "should return nothing (filter reject)",
                    content: (filter) => () => {
                        const [h1, , h2] = insertTestHtml(`<h1>a</h1><p>b</p><h2>c</h2>`);
                        // From h1 to "c":
                        const nodes = getNodesInRange([h1, h2.firstChild], { filter });
                        expect(nodes).toEqual([]);
                    },
                    filter: (node) =>
                        isElement(node) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
                },
            ];
            for (const { name, content, filter } of filterTests) {
                test(name + " (as function)", content(filter));
            }
            for (const { name, content, filter } of filterTests) {
                test(name + " (as acceptNode)", content({ acceptNode: filter }));
            }
            test("should return only text nodes with more than one character (whatToShow + filter", () => {
                const [h1, p1, , h2] = insertTestHtml(`<h1>ab</h1><p>cd</p><p>e</p><h2>fg</h2>`);
                // From h1 to "fg":
                const nodes = getNodesInRange([h1, h2.firstChild], {
                    whatToShow: NodeFilter.SHOW_TEXT,
                    filter: (node) =>
                        node.textContent.length > 1
                            ? NodeFilter.FILTER_ACCEPT
                            : NodeFilter.FILTER_SKIP,
                });
                expect(nodes).toEqual([h1.firstChild, p1.firstChild, h2.firstChild]);
            });
        });
    });
    describe("complex html", () => {
        const complexHtml = unformat(
            `<div>
                <p>ab
                    <span>c<i>d</i><span>e</span></span>
                    <span>f</span>g
                </p>
                <h1>h</h1>
                <a href="#">i<span>j</span></a>
            </div>
            <p>k</p>
            <ul>
                <li>l</li>
                <li>
                    <p>m</p>
                    <p>n</p>
                </li>
                <li>
                    <ul>
                        <li class="oe-nested">
                            <ol>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li>opq</li>
                                    </ul>
                                </li>
                            </ol>
                        </li>
                    </ul>
                </li>
                <li>rs<i>tu</i>vw</li>
            </ul>
            <p>xy</p>`
        );
        const getNodeKey = (node, object) => {
            let key;
            if (isTextNode(node)) {
                key = node.textContent;
            } else {
                key = node.nodeName.toLowerCase();
                if (key in object) {
                    let i = 2;
                    while (key + i in object) {
                        i += 1;
                    }
                    key = key + i;
                }
            }
            return key;
        };
        const representNodeChildren = (node) =>
            [...node.childNodes].reduce((accumulator, child) => {
                const key = getNodeKey(child, accumulator);
                accumulator[key] = { node: child, ...representNodeChildren(child) };
                return accumulator;
            }, {});
        const insertAndGetComplexHtml = () => {
            const p2 = insertTestHtml(complexHtml)[3];
            p2.append(p2.ownerDocument.createTextNode("z"));
            return representNodeChildren(p2.parentElement);
        };
        const toNodes = (...nodeReprs) => nodeReprs.map((nodeRepr) => nodeRepr.node);
        test("should return the nodes between a block and a text node", () => {
            const { div, p, ul, p2 } = insertAndGetComplexHtml();
            // From "div" to "z":
            const nodes = getNodesInRange(toNodes(div, p2.z));
            // prettier-ignore
            expect(nodes).toEqual(toNodes(
                div,
                    div.p, div.p.ab,
                        div.p.span,
                        div.p.span.c, div.p.span.i, div.p.span.i.d, div.p.span.span, div.p.span.span.e,
                        div.p.span2, div.p.span2.f, div.p.g,
                    div.h1, div.h1.h,
                    div.a, div.a.i, div.a.span, div.a.span.j,
                p, p.k,
                ul,
                    ul.li, ul.li.l,
                    ul.li2, ul.li2.p, ul.li2.p.m, ul.li2.p2, ul.li2.p2.n,
                    ul.li3, ul.li3.ul,
                        ul.li3.ul.li, ul.li3.ul.li.ol,
                            ul.li3.ul.li.ol.li, ul.li3.ul.li.ol.li.ul,
                                ul.li3.ul.li.ol.li.ul.li, ul.li3.ul.li.ol.li.ul.li.opq,
                    ul.li4, ul.li4.rs, ul.li4.i, ul.li4.i.tu, ul.li4.vw,
                p2, p2.xy, p2.z
            ));
        });
        test("should return the nodes between two blocks", () => {
            const { div, p, ul, p2 } = insertAndGetComplexHtml();
            // From div to p2:
            const nodes = getNodesInRange(toNodes(div, p2));
            // prettier-ignore
            expect(nodes).toEqual(toNodes(
                div,
                    div.p, div.p.ab,
                        div.p.span,
                        div.p.span.c, div.p.span.i, div.p.span.i.d, div.p.span.span, div.p.span.span.e,
                        div.p.span2, div.p.span2.f, div.p.g,
                    div.h1, div.h1.h,
                    div.a, div.a.i, div.a.span, div.a.span.j,
                p, p.k,
                ul,
                    ul.li, ul.li.l,
                    ul.li2, ul.li2.p, ul.li2.p.m, ul.li2.p2, ul.li2.p2.n,
                    ul.li3, ul.li3.ul,
                        ul.li3.ul.li, ul.li3.ul.li.ol,
                            ul.li3.ul.li.ol.li, ul.li3.ul.li.ol.li.ul,
                                ul.li3.ul.li.ol.li.ul.li, ul.li3.ul.li.ol.li.ul.li.opq,
                    ul.li4, ul.li4.rs, ul.li4.i, ul.li4.i.tu, ul.li4.vw,
                p2
            ));
        });
        test("should return the nodes between two nested elements", () => {
            const { div, p, ul } = insertAndGetComplexHtml();
            // From div > p > span > i to ul > li3 > ul > li > ol > li > ul > li > opq:
            const nodes = getNodesInRange(toNodes(div.p.span.i, ul.li3.ul.li.ol.li.ul.li.opq));
            // prettier-ignore
            expect(nodes).toEqual(toNodes(
                        div.p.span.i, div.p.span.i.d, div.p.span.span, div.p.span.span.e,
                        div.p.span2, div.p.span2.f, div.p.g,
                    div.h1, div.h1.h,
                    div.a, div.a.i, div.a.span, div.a.span.j,
                p, p.k,
                ul,
                    ul.li, ul.li.l,
                    ul.li2, ul.li2.p, ul.li2.p.m, ul.li2.p2, ul.li2.p2.n,
                    ul.li3, ul.li3.ul,
                        ul.li3.ul.li, ul.li3.ul.li.ol,
                            ul.li3.ul.li.ol.li, ul.li3.ul.li.ol.li.ul,
                                ul.li3.ul.li.ol.li.ul.li, ul.li3.ul.li.ol.li.ul.li.opq,
            ));
        });
        test("should return the nodes between a nested text node and a nested block", () => {
            const { div, p, ul } = insertAndGetComplexHtml();
            // From "g" to ul:
            const nodes = getNodesInRange(toNodes(div.p.g, ul));
            // prettier-ignore
            expect(nodes).toEqual(toNodes(
                        div.p.g,
                    div.h1, div.h1.h,
                    div.a, div.a.i, div.a.span, div.a.span.j,
                p, p.k,
                ul
            ));
        });
        test("should return the nodes between two nested text nodes", () => {
            const { div, p, ul, p2 } = insertAndGetComplexHtml();
            // From "c" to "xy":
            const nodes = getNodesInRange(toNodes(div.p.span.c, p2.xy));
            // prettier-ignore
            expect(nodes).toEqual(toNodes(
                        div.p.span.c, div.p.span.i, div.p.span.i.d, div.p.span.span, div.p.span.span.e,
                        div.p.span2, div.p.span2.f, div.p.g,
                    div.h1, div.h1.h,
                    div.a, div.a.i, div.a.span, div.a.span.j,
                p, p.k,
                ul,
                    ul.li, ul.li.l,
                    ul.li2, ul.li2.p, ul.li2.p.m, ul.li2.p2, ul.li2.p2.n,
                    ul.li3, ul.li3.ul,
                        ul.li3.ul.li, ul.li3.ul.li.ol,
                            ul.li3.ul.li.ol.li, ul.li3.ul.li.ol.li.ul,
                                ul.li3.ul.li.ol.li.ul.li, ul.li3.ul.li.ol.li.ul.li.opq,
                    ul.li4, ul.li4.rs, ul.li4.i, ul.li4.i.tu, ul.li4.vw,
                p2, p2.xy
            ));
        });
    });
});
