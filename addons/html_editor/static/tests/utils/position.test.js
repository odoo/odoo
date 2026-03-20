import {
    boundariesIn,
    boundariesOut,
    childNodeIndex,
    endPos,
    leftPos,
    nodeSize,
    rightPos,
    startPos,
} from "@html_editor/utils/position";
import { describe, expect, test } from "@odoo/hoot";
import { insertTestHtml } from "../_helpers/editor";

describe("leftPos", () => {
    test("should return the left position of a lonely text node", () => {
        const [p] = insertTestHtml("<p>a</p>");
        const a = p.firstChild;
        const result = leftPos(a);
        expect(result).toEqual([p, 0]);
    });

    test("should return the left position of an inline element", () => {
        const [p] = insertTestHtml("<p><b>a</b></p>");
        const b = p.childNodes[0];
        const result = leftPos(b);
        expect(result).toEqual([p, 0]);
    });

    test("should return the left position of an inline element with whitespace", () => {
        const [p] = insertTestHtml(
            `<p>
                <b>a</b>
            </p>`
        );
        const b = p.childNodes[1];
        const result = leftPos(b);
        expect(result).toEqual([p, 1]);
    });

    test("should return the left position of sibling-rich inline element", () => {
        const [p] = insertTestHtml(
            `<p>
                abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
            </p>`
        );
        const i = p.childNodes[3];
        const result = leftPos(i);
        expect(result).toEqual([p, 3]);
    });
});

describe("rightPos", () => {
    test("should return the right position of a lonely text node", () => {
        const [p] = insertTestHtml("<p>a</p>");
        const a = p.firstChild;
        const result = rightPos(a);
        expect(result).toEqual([p, 1]);
    });

    test("should return the right position of an inline element", () => {
        const [p] = insertTestHtml("<p><b>a</b></p>");
        const b = p.childNodes[0];
        const result = rightPos(b);
        expect(result).toEqual([p, 1]);
    });

    test("should return the right position of an inline element with whitespace", () => {
        const [p] = insertTestHtml(
            `<p>
                <b>a</b>
            </p>`
        );
        const b = p.childNodes[1];
        const result = rightPos(b);
        expect(result).toEqual([p, 2]);
    });

    test("should return the right position of sibling-rich inline element", () => {
        const [p] = insertTestHtml(
            `<p>
                abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
            </p>`
        );
        const i = p.childNodes[3];
        const result = rightPos(i);
        expect(result).toEqual([p, 4]);
    });
});

describe("boundariesOut", () => {
    test("should return the outside bounds of a lonely text node", () => {
        const [p] = insertTestHtml("<p>a</p>");
        const a = p.firstChild;
        const result = boundariesOut(a);
        expect(result).toEqual([p, 0, p, 1]);
    });

    test("should return the outside bounds of an inline element", () => {
        const [p] = insertTestHtml("<p><b>a</b></p>");
        const b = p.childNodes[0];
        const result = boundariesOut(b);
        expect(result).toEqual([p, 0, p, 1]);
    });

    test("should return the outside bounds of an inline element with whitespace", () => {
        const [p] = insertTestHtml(
            `<p>
                <b>a</b>
            </p>`
        );
        const b = p.childNodes[1];
        const result = boundariesOut(b);
        expect(result).toEqual([p, 1, p, 2]);
    });

    test("should return the outside bounds of sibling-rich inline element", () => {
        const [p] = insertTestHtml(
            `<p>
                abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
            </p>`
        );
        const i = p.childNodes[3];
        const result = boundariesOut(i);
        expect(result).toEqual([p, 3, p, 4]);
    });
});

describe("startPos", () => {
    test("should return the start position of a lonely text node", () => {
        const [p] = insertTestHtml("<p>a</p>");
        const a = p.firstChild;
        const result = startPos(a);
        expect(result).toEqual([a, 0]);
    });

    test("should return the start position of an inline element", () => {
        const [p] = insertTestHtml("<p><b>a</b></p>");
        const b = p.childNodes[0];
        const result = startPos(b);
        expect(result).toEqual([b, 0]);
    });

    test("should return the start position of an inline element with whitespace", () => {
        const [p] = insertTestHtml(
            `<p>
                <b>a</b>
            </p>`
        );
        const b = p.childNodes[1];
        const result = startPos(b);
        expect(result).toEqual([b, 0]);
    });

    test("should return the start position of sibling-rich inline element", () => {
        const [p] = insertTestHtml(
            `<p>
                abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
            </p>`
        );
        const i = p.childNodes[3];
        const result = startPos(i);
        expect(result).toEqual([i, 0]);
    });
});

describe("endPos", () => {
    test("should return the end position of a lonely text node", () => {
        const [p] = insertTestHtml("<p>a</p>");
        const a = p.firstChild;
        const result = endPos(a);
        expect(result).toEqual([a, 1]);
    });

    test("should return the end position of an inline element", () => {
        const [p] = insertTestHtml("<p><b>a</b></p>");
        const b = p.childNodes[0];
        const result = endPos(b);
        expect(result).toEqual([b, 1]);
    });

    test("should return the end position of an inline element with whitespace", () => {
        const [p] = insertTestHtml(
            `<p>
                <b>a</b>
            </p>`
        );
        const b = p.childNodes[1];
        const result = endPos(b);
        expect(result).toEqual([b, 1]);
    });

    test("should return the end position of sibling-rich inline element", () => {
        const [p] = insertTestHtml(
            `<p>
                abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
            </p>`
        );
        const i = p.childNodes[3];
        const result = endPos(i);
        expect(result).toEqual([i, 1]);
    });
});

describe("boundariesIn", () => {
    test("should return the inside bounds of a lonely text node", () => {
        const [p] = insertTestHtml("<p>a</p>");
        const a = p.firstChild;
        const result = boundariesIn(a);
        expect(result).toEqual([a, 0, a, 1]);
    });

    test("should return the inside bounds of an inline element", () => {
        const [p] = insertTestHtml("<p><b>a</b></p>");
        const b = p.childNodes[0];
        const result = boundariesIn(b);
        expect(result).toEqual([b, 0, b, 1]);
    });

    test("should return the inside bounds of an inline element with whitespace", () => {
        const [p] = insertTestHtml(
            `<p>
                <b>a</b>
            </p>`
        );
        const b = p.childNodes[1];
        const result = boundariesIn(b);
        expect(result).toEqual([b, 0, b, 1]);
    });

    test("should return the inside bounds of sibling-rich inline element", () => {
        const [p] = insertTestHtml(
            `<p>
                abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
            </p>`
        );
        const i = p.childNodes[3];
        const result = boundariesIn(i);
        expect(result).toEqual([i, 0, i, 1]);
    });
});

describe("childNodeIndex", () => {
    test("should return the index of a lonely text node", () => {
        const [p] = insertTestHtml("<p>a</p>");
        p.childNodes.forEach((child, index) => {
            expect(childNodeIndex(child)).toBe(index);
        });
    });

    test("should return the index of an inline element", () => {
        const [p] = insertTestHtml("<p><b>a</b></p>");
        p.childNodes.forEach((child, index) => {
            expect(childNodeIndex(child)).toBe(index);
        });
    });

    test("should return the index of an inline element with whitespace", () => {
        const [p] = insertTestHtml(
            `<p>
                <b>a</b>
            </p>`
        );
        p.childNodes.forEach((child, index) => {
            expect(childNodeIndex(child)).toBe(index);
        });
    });

    test("should return the index of sibling-rich inline element", () => {
        const [p] = insertTestHtml(
            `<p>
                abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
            </p>`
        );
        p.childNodes.forEach((child, index) => {
            expect(childNodeIndex(child)).toBe(index);
        });
    });
});

describe("nodeSize", () => {
    test("should return the size of a simple element", () => {
        const [p] = insertTestHtml("<p>a</p>");
        const result = nodeSize(p);
        expect(result).toBe(1);
    });

    test("should return the size of a text node", () => {
        const [p] = insertTestHtml("<p>abc</p>");
        const result = nodeSize(p.firstChild);
        expect(result).toBe(3);
    });

    test("should return the size of a child-rich element", () => {
        const [p] = insertTestHtml(
            `<p>
                a<b>bc</b>d<i>ef</i>
            </p>`
        );
        const result = nodeSize(p);
        expect(result).toBe(5);
    });
});
