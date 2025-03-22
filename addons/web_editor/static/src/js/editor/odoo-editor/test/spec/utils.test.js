import {
    ancestors,
    boundariesIn,
    boundariesOut,
    childNodeIndex,
    closestBlock,
    closestElement,
    descendants,
    endPos,
    ensureFocus,
    firstLeaf,
    getAdjacentPreviousSiblings,
    getAdjacentNextSiblings,
    getAdjacents,
    getDeepRange,
    getNormalizedCursorPosition,
    getSelectedNodes,
    getTraversedNodes,
    isVisible,
    isVisibleStr,
    lastLeaf,
    leftPos,
    nextLeaf,
    nodeSize,
    previousLeaf,
    rightPos,
    startPos,
    setSelection,
    setCursorStart,
    setCursorEnd,
    splitAroundUntil,
    splitTextNode,
    getCursorDirection,
    DIRECTIONS,
    isBlock,
    isVisibleTextNode,
    CTYPES,
    getState,
    restoreState,
    enforceWhitespace,
} from '../../src/utils/utils.js';
import {
    BasicEditor,
    insertText,
    nextTickFrame,
    testEditor,
    triggerEvent,
    unformat,
} from '../utils.js';

const cleanTestHtml = () => {
    const testElements = document.querySelectorAll('body>div[contenteditable=true]');
    Array.prototype.forEach.call(testElements, function(node) {
        node.parentNode.removeChild(node);
    });
    return true;
};
const insertTestHtml = innerHtml => {
    cleanTestHtml();
    const container = document.createElement('DIV');
    container.setAttribute('contenteditable', true);
    container.innerHTML = innerHtml;
    document.body.appendChild(container);
    return container.childNodes;
};

describe('Utils', () => {
    afterEach(cleanTestHtml);

    //------------------------------------------------------------------------------
    // Position and sizes
    //------------------------------------------------------------------------------

    describe('leftPos', () => {
        it('should return the left position of a lonely text node', () => {
            const [p] = insertTestHtml('<p>a</p>');
            const a = p.firstChild;
            const result = leftPos(a);
            window.chai.expect(result).to.eql([p, 0]);
        });
        it('should return the left position of an inline element', () => {
            const [p] = insertTestHtml('<p><b>a</b></p>');
            const b = p.childNodes[0];
            const result = leftPos(b);
            window.chai.expect(result).to.eql([p, 0]);
        });
        it('should return the left position of an inline element with whitespace', () => {
            const [p] = insertTestHtml(
                `<p>
                    <b>a</b>
                </p>`,
            );
            const b = p.childNodes[1];
            const result = leftPos(b);
            window.chai.expect(result).to.eql([p, 1]);
        });
        it('should return the left position of sibling-rich inline element', () => {
            const [p] = insertTestHtml(
                `<p>
                    abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
                </p>`,
            );
            const i = p.childNodes[3];
            const result = leftPos(i);
            window.chai.expect(result).to.eql([p, 3]);
        });
    });
    describe('rightPos', () => {
        it('should return the right position of a lonely text node', () => {
            const [p] = insertTestHtml('<p>a</p>');
            const a = p.firstChild;
            const result = rightPos(a);
            window.chai.expect(result).to.eql([p, 1]);
        });
        it('should return the right position of an inline element', () => {
            const [p] = insertTestHtml('<p><b>a</b></p>');
            const b = p.childNodes[0];
            const result = rightPos(b);
            window.chai.expect(result).to.eql([p, 1]);
        });
        it('should return the right position of an inline element with whitespace', () => {
            const [p] = insertTestHtml(
                `<p>
                    <b>a</b>
                </p>`,
            );
            const b = p.childNodes[1];
            const result = rightPos(b);
            window.chai.expect(result).to.eql([p, 2]);
        });
        it('should return the right position of sibling-rich inline element', () => {
            const [p] = insertTestHtml(
                `<p>
                    abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
                </p>`,
            );
            const i = p.childNodes[3];
            const result = rightPos(i);
            window.chai.expect(result).to.eql([p, 4]);
        });
    });
    describe('boundariesOut', () => {
        it('should return the outside bounds of a lonely text node', () => {
            const [p] = insertTestHtml('<p>a</p>');
            const a = p.firstChild;
            const result = boundariesOut(a);
            window.chai.expect(result).to.eql([p, 0, p, 1]);
        });
        it('should return the outside bounds of an inline element', () => {
            const [p] = insertTestHtml('<p><b>a</b></p>');
            const b = p.childNodes[0];
            const result = boundariesOut(b);
            window.chai.expect(result).to.eql([p, 0, p, 1]);
        });
        it('should return the outside bounds of an inline element with whitespace', () => {
            const [p] = insertTestHtml(
                `<p>
                    <b>a</b>
                </p>`,
            );
            const b = p.childNodes[1];
            const result = boundariesOut(b);
            window.chai.expect(result).to.eql([p, 1, p, 2]);
        });
        it('should return the outside bounds of sibling-rich inline element', () => {
            const [p] = insertTestHtml(
                `<p>
                    abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
                </p>`,
            );
            const i = p.childNodes[3];
            const result = boundariesOut(i);
            window.chai.expect(result).to.eql([p, 3, p, 4]);
        });
    });
    describe('startPos', () => {
        it('should return the start position of a lonely text node', () => {
            const [p] = insertTestHtml('<p>a</p>');
            const a = p.firstChild;
            const result = startPos(a);
            window.chai.expect(result).to.eql([a, 0]);
        });
        it('should return the start position of an inline element', () => {
            const [p] = insertTestHtml('<p><b>a</b></p>');
            const b = p.childNodes[0];
            const result = startPos(b);
            window.chai.expect(result).to.eql([b, 0]);
        });
        it('should return the start position of an inline element with whitespace', () => {
            const [p] = insertTestHtml(
                `<p>
                    <b>a</b>
                </p>`,
            );
            const b = p.childNodes[1];
            const result = startPos(b);
            window.chai.expect(result).to.eql([b, 0]);
        });
        it('should return the start position of sibling-rich inline element', () => {
            const [p] = insertTestHtml(
                `<p>
                    abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
                </p>`,
            );
            const i = p.childNodes[3];
            const result = startPos(i);
            window.chai.expect(result).to.eql([i, 0]);
        });
    });
    describe('endPos', () => {
        it('should return the end position of a lonely text node', () => {
            const [p] = insertTestHtml('<p>a</p>');
            const a = p.firstChild;
            const result = endPos(a);
            window.chai.expect(result).to.eql([a, 1]);
        });
        it('should return the end position of an inline element', () => {
            const [p] = insertTestHtml('<p><b>a</b></p>');
            const b = p.childNodes[0];
            const result = endPos(b);
            window.chai.expect(result).to.eql([b, 1]);
        });
        it('should return the end position of an inline element with whitespace', () => {
            const [p] = insertTestHtml(
                `<p>
                    <b>a</b>
                </p>`,
            );
            const b = p.childNodes[1];
            const result = endPos(b);
            window.chai.expect(result).to.eql([b, 1]);
        });
        it('should return the end position of sibling-rich inline element', () => {
            const [p] = insertTestHtml(
                `<p>
                    abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
                </p>`,
            );
            const i = p.childNodes[3];
            const result = endPos(i);
            window.chai.expect(result).to.eql([i, 1]);
        });
    });
    describe('boundariesIn', () => {
        it('should return the inside bounds of a lonely text node', () => {
            const [p] = insertTestHtml('<p>a</p>');
            const a = p.firstChild;
            const result = boundariesIn(a);
            window.chai.expect(result).to.eql([a, 0, a, 1]);
        });
        it('should return the inside bounds of an inline element', () => {
            const [p] = insertTestHtml('<p><b>a</b></p>');
            const b = p.childNodes[0];
            const result = boundariesIn(b);
            window.chai.expect(result).to.eql([b, 0, b, 1]);
        });
        it('should return the inside bounds of an inline element with whitespace', () => {
            const [p] = insertTestHtml(
                `<p>
                    <b>a</b>
                </p>`,
            );
            const b = p.childNodes[1];
            const result = boundariesIn(b);
            window.chai.expect(result).to.eql([b, 0, b, 1]);
        });
        it('should return the inside bounds of sibling-rich inline element', () => {
            const [p] = insertTestHtml(
                `<p>
                    abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
                </p>`,
            );
            const i = p.childNodes[3];
            const result = boundariesIn(i);
            window.chai.expect(result).to.eql([i, 0, i, 1]);
        });
    });
    describe('childNodeIndex', () => {
        it('should return the index of a lonely text node', () => {
            const [p] = insertTestHtml('<p>a</p>');
            p.childNodes.forEach((child, index) => {
                window.chai.expect(childNodeIndex(child)).to.equal(index);
            });
        });
        it('should return the index of an inline element', () => {
            const [p] = insertTestHtml('<p><b>a</b></p>');
            p.childNodes.forEach((child, index) => {
                window.chai.expect(childNodeIndex(child)).to.equal(index);
            });
        });
        it('should return the index of an inline element with whitespace', () => {
            const [p] = insertTestHtml(
                `<p>
                    <b>a</b>
                </p>`,
            );
            p.childNodes.forEach((child, index) => {
                window.chai.expect(childNodeIndex(child)).to.equal(index);
            });
        });
        it('should return the index of sibling-rich inline element', () => {
            const [p] = insertTestHtml(
                `<p>
                    abc<b>def</b>ghi<i>jkl</i><span><u>mno</u></span>pqr
                </p>`,
            );
            p.childNodes.forEach((child, index) => {
                window.chai.expect(childNodeIndex(child)).to.equal(index);
            });
        });
    });
    describe('nodeSize', () => {
        it('should return the size of a simple element', () => {
            const [p] = insertTestHtml('<p>a</p>');
            const result = nodeSize(p);
            window.chai.expect(result).to.equal(1);
        });
        it('should return the size of a text node', () => {
            const [p] = insertTestHtml('<p>abc</p>');
            const result = nodeSize(p.firstChild);
            window.chai.expect(result).to.equal(3);
        });
        it('should return the size of a child-rich element', () => {
            const [p] = insertTestHtml(
                `<p>
                    a<b>bc</b>d<i>ef</i>
                </p>`,
            );
            const result = nodeSize(p);
            window.chai.expect(result).to.equal(5);
        });
    });

    //------------------------------------------------------------------------------
    // DOM Path and node search functions
    //------------------------------------------------------------------------------

    // TODO: test path functions:
    // - closestPath
    // - findNode
    // - createDOMPathGenerator
    describe('closestElement', () => {
        it('should find the closest element to a text node', () => {
            const [div] = insertTestHtml('<div><p>abc</p></div>');
            const p = div.firstChild;
            const abc = p.firstChild;
            const result = closestElement(abc);
            window.chai.expect(result).to.equal(p);
        });
        it('should find that the closest element to an element is itself', () => {
            const [p] = insertTestHtml('<p>abc</p>');
            const result = closestElement(p);
            window.chai.expect(result).to.equal(p);
        });
    });
    describe('ancestors', () => {
        it('should find all the ancestors of a text node', () => {
            const [div] = insertTestHtml(
                '<div><div><div><p>abc</p><div><p>def</p></div></div></div></div>',
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
            window.chai.expect(result).to.eql(abcAncestors);
        });
        it('should find only the editable', () => {
            const [p] = insertTestHtml('<p>abc</p>');
            const editable = p.parentElement;
            const result = ancestors(p, editable);
            window.chai.expect(result).to.eql([editable]);
        });
    });
    describe('descendants', () => {
        it('should find all the descendants of a div in depth-first order', () => {
            const [div] = insertTestHtml(
                '<div><div><div><p>abc</p><div><p>def</p></div></div></div></div>',
            );
            window.chai.expect(descendants(div)).to.eql([
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
    describe('closestBlock', () => {
        it('should find the closest block of a deeply nested text node', () => {
            const [div] = insertTestHtml(
                '<div><div><p>ab<b><i><u>cd</u></i></b>ef</p></div></div>',
            );
            const p = div.firstChild.firstChild;
            const cd = p.childNodes[1].firstChild.firstChild.firstChild;
            const result = closestBlock(cd);
            window.chai.expect(result).to.equal(p);
        });
        it('should find that the closest block to a block is itself', () => {
            const [div] = insertTestHtml('<div><div><p>ab</p></div></div>');
            const p = div.firstChild.firstChild;
            const result = closestBlock(p);
            window.chai.expect(result).to.equal(p);
        });
        it('should return null if no block ancestor', () => {
            const node = document.createTextNode('\n        ');
            window.chai.expect(closestBlock(node)).to.equal(null);
            window.chai.expect(isVisibleTextNode(node)).to.equal(false);
        });
    });
    describe('lastLeaf', () => {
        it('should find the last leaf of a child-rich block', () => {
            const [div] = insertTestHtml(
                '<div><div><p>ab<span>cd</span><b><i><u>ef</u></i></b></p></div></div>',
            );
            const p = div.firstChild.firstChild;
            const ef = p.childNodes[2].firstChild.firstChild.firstChild;
            const result = lastLeaf(div);
            window.chai.expect(result).to.equal(ef);
        });
        it('should find that the last closest block descendant of a child-rich block is itself', () => {
            const [div] = insertTestHtml(
                '<div><div><p>ab<span>cd</span><b><i><u>ef</u></i></b></p></div></div>',
            );
            const result = lastLeaf(div, isBlock);
            window.chai.expect(result).to.equal(div);
        });
        it('should find no last closest block descendant of a child-rich inline and return its last leaf instead', () => {
            const [div] = insertTestHtml(
                '<div><div><p>ab<span>cd</span><b><i><u>ef</u></i></b></p></div></div>',
            );
            const b = div.firstChild.firstChild.childNodes[2];
            const ef = b.firstChild.firstChild.firstChild;
            const result = lastLeaf(b, isBlock);
            window.chai.expect(result).to.equal(ef);
        });
    });
    describe('firstLeaf', () => {
        it('should find the first leaf of a child-rich block', () => {
            const [div] = insertTestHtml(
                '<div><div><p><b><i><u>ab</u></i></b><span>cd</span>ef</p></div></div>',
            );
            const p = div.firstChild.firstChild;
            const ab = p.firstChild.firstChild.firstChild.firstChild;
            const result = firstLeaf(div);
            window.chai.expect(result).to.equal(ab);
        });
        it('should find that the first closest block descendant of a child-rich block is itself', () => {
            const [div] = insertTestHtml(
                '<div><div><p>ab<span>cd</span><b><i><u>ef</u></i></b></p></div></div>',
            );
            const result = firstLeaf(div, isBlock);
            window.chai.expect(result).to.equal(div);
        });
        it('should find no first closest block descendant of a child-rich inline and return its first leaf instead', () => {
            const [div] = insertTestHtml(
                '<div><div><p><b><i><u>ab</u></i></b><span>cd</span>ef</p></div></div>',
            );
            const b = div.firstChild.firstChild.firstChild;
            const ab = b.firstChild.firstChild.firstChild;
            const result = firstLeaf(b, isBlock);
            window.chai.expect(result).to.equal(ab);
        });
    });
    describe('previousLeaf', () => {
        it('should find the previous leaf of a deeply nested node', () => {
            const [div] = insertTestHtml(
                '<div><div><p><b>ab<i>cd<u>ef</u>gh</i></b><span>ij</span>kl</p></div></div>',
            );
            const editable = div.parentElement;
            const p = div.firstChild.firstChild;
            const gh = p.firstChild.childNodes[1].childNodes[2];
            const ij = p.childNodes[1].firstChild;
            const result = previousLeaf(ij, editable);
            window.chai.expect(result).to.equal(gh);
        });
        it('should find no previous leaf and return undefined', () => {
            const [div] = insertTestHtml(
                '<div><div><p><b>ab<i>cd<u>ef</u>gh</i></b><span>ij</span>kl</p></div></div>',
            );
            const editable = div.parentElement;
            const p = div.firstChild.firstChild;
            const ab = p.firstChild.firstChild;
            const result = previousLeaf(ab, editable);
            window.chai.expect(result).to.equal(undefined);
        });
        it('should find the previous leaf of a deeply nested node, skipping invisible nodes', () => {
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
                </div>`,
            );
            const editable = div.parentElement;
            const p1 = div.childNodes[1].childNodes[1];
            const gh = p1.childNodes[1].childNodes[1].childNodes[2];
            const p2 = div.childNodes[1].childNodes[3];
            const ij = p2.childNodes[1].firstChild;
            const result = previousLeaf(ij, editable, true);
            window.chai.expect(result).to.equal(gh);
        });
        it('should find no previous leaf, skipping invisible nodes, and return undefined', () => {
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
                </div>`,
            );
            const editable = div.parentElement;
            const p1 = div.childNodes[1].childNodes[1];
            const ab = p1.childNodes[1].firstChild;
            const result = previousLeaf(ab, editable, true);
            window.chai.expect(result).to.equal(undefined);
        });
        it('should find the previous leaf of a deeply nested node to be whitespace', () => {
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
                </div>`,
            );
            const editable = div.parentElement;
            const p2 = div.childNodes[1].childNodes[3];
            const whitespace = p2.firstChild;
            const ij = p2.childNodes[1].firstChild;
            const result = previousLeaf(ij, editable);
            window.chai.expect(result).to.equal(whitespace);
            window.chai.expect(isVisibleStr(whitespace)).to.equal(false);
        });
    });
    describe('nextLeaf', () => {
        it('should find the next leaf of a deeply nested node', () => {
            const [div] = insertTestHtml(
                '<div><div><p><b>ab<i>cd<u>ef</u>gh</i></b><span>ij</span>kl</p></div></div>',
            );
            const editable = div.parentElement;
            const p = div.firstChild.firstChild;
            const gh = p.firstChild.childNodes[1].childNodes[2];
            const ij = p.childNodes[1].firstChild;
            const result = nextLeaf(gh, editable);
            window.chai.expect(result).to.equal(ij);
        });
        it('should find no next leaf and return undefined', () => {
            const [div] = insertTestHtml(
                '<div><div><p><b>ab<i>cd<u>ef</u>gh</i></b><span>ij</span>kl</p></div></div>',
            );
            const editable = div.parentElement;
            const p = div.firstChild.firstChild;
            const kl = p.childNodes[2];
            const result = nextLeaf(kl, editable);
            window.chai.expect(result).to.equal(undefined);
        });
        it('should find the next leaf of a deeply nested node, skipping invisible nodes', () => {
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
                </div>`,
            );
            const editable = div.parentElement;
            const p1 = div.childNodes[1].childNodes[1];
            const gh = p1.childNodes[1].childNodes[1].childNodes[2];
            const p2 = div.childNodes[1].childNodes[3];
            const ij = p2.childNodes[1].firstChild;
            const result = nextLeaf(gh, editable, true);
            window.chai.expect(result).to.equal(ij);
        });
        it('should find no next leaf, skipping invisible nodes, and return undefined', () => {
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
                </div>`,
            );
            const editable = div.parentElement;
            const p2 = div.childNodes[1].childNodes[3];
            const kl = p2.childNodes[2];
            const result = nextLeaf(kl, editable, true);
            window.chai.expect(result).to.equal(undefined);
        });
        it('should find the next leaf of a deeply nested node to be whitespace', () => {
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
                </div>`,
            );
            const editable = div.parentElement;
            const p2 = div.childNodes[1].childNodes[3];
            const kl = p2.childNodes[2];
            const whitespace = div.childNodes[1].childNodes[4];
            const result = nextLeaf(kl, editable);
            window.chai.expect(result).to.equal(whitespace);
            window.chai.expect(isVisibleStr(whitespace)).to.equal(false);
        });
    });
    describe('getAdjacentPreviousSiblings', () => {
        it('should find the adjacent previous siblings of a deeply nested node', () => {
            const [p] = insertTestHtml('<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>');
            const gh = p.firstChild.childNodes[1].childNodes[2];
            const u = gh.previousSibling;
            const cd = u.previousSibling;
            const result = getAdjacentPreviousSiblings(gh);
            window.chai.expect(result).to.eql([u, cd]);
        });
        it('should find no adjacent previous siblings of a deeply nested node', () => {
            const [p] = insertTestHtml('<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>');
            const ij = p.firstChild.childNodes[1].childNodes[3].firstChild;
            const result = getAdjacentPreviousSiblings(ij);
            window.chai.expect(result).to.eql([]);
        });
        it('should find only the adjacent previous siblings of a deeply nested node that are elements', () => {
            const [p] = insertTestHtml('<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>');
            const gh = p.firstChild.childNodes[1].childNodes[2];
            const u = gh.previousSibling;
            const result = getAdjacentPreviousSiblings(
                gh,
                node => node.nodeType === Node.ELEMENT_NODE,
            );
            window.chai.expect(result).to.eql([u]);
        });
        it('should find only the adjacent previous siblings of a deeply nested node that are text nodes (none)', () => {
            const [p] = insertTestHtml('<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>');
            const gh = p.firstChild.childNodes[1].childNodes[2];
            const result = getAdjacentPreviousSiblings(
                gh,
                node => node.nodeType === Node.TEXT_NODE,
            );
            window.chai.expect(result).to.eql([]);
        });
    });
    describe('getAdjacentNextSiblings', () => {
        it('should find the adjacent next siblings of a deeply nested node', () => {
            const [p] = insertTestHtml('<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>');
            const gh = p.firstChild.childNodes[1].childNodes[2];
            const span = gh.nextSibling;
            const kl = span.nextSibling;
            const result = getAdjacentNextSiblings(gh);
            window.chai.expect(result).to.eql([span, kl]);
        });
        it('should find no adjacent next siblings of a deeply nested node', () => {
            const [p] = insertTestHtml('<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>');
            const ij = p.firstChild.childNodes[1].childNodes[3].firstChild;
            const result = getAdjacentNextSiblings(ij);
            window.chai.expect(result).to.eql([]);
        });
        it('should find only the adjacent next siblings of a deeply nested node that are elements', () => {
            const [p] = insertTestHtml('<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>');
            const gh = p.firstChild.childNodes[1].childNodes[2];
            const span = gh.nextSibling;
            const result = getAdjacentNextSiblings(gh, node => node.nodeType === Node.ELEMENT_NODE);
            window.chai.expect(result).to.eql([span]);
        });
        it('should find only the adjacent next siblings of a deeply nested node that are text nodes (none)', () => {
            const [p] = insertTestHtml('<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>');
            const gh = p.firstChild.childNodes[1].childNodes[2];
            const result = getAdjacentNextSiblings(gh, node => node.nodeType === Node.TEXT_NODE);
            window.chai.expect(result).to.eql([]);
        });
    });
    describe('getAdjacents', () => {
        it('should find the adjacent siblings of a deeply nested node', () => {
            const [p] = insertTestHtml('<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>');
            const gh = p.firstChild.childNodes[1].childNodes[2];
            const u = gh.previousSibling;
            const cd = u.previousSibling;
            const span = gh.nextSibling;
            const kl = span.nextSibling;
            const result = getAdjacents(gh);
            window.chai.expect(result).to.eql([cd, u, gh, span, kl]);
        });
        it('should find no adjacent siblings of a deeply nested node', () => {
            const [p] = insertTestHtml('<p><b>ab<i>cd<u>ef</u>gh<span>ij</span>kl</i>mn</b>op</p>');
            const ij = p.firstChild.childNodes[1].childNodes[3].firstChild;
            const result = getAdjacents(ij);
            window.chai.expect(result).to.eql([ij]);
        });
        it('should find the adjacent siblings of a deeply nested node that are elements', () => {
            const [p] = insertTestHtml(
                '<p><b>ab<i>cd<u>ef</u><span>gh</span><span>ij</span>kl</i>mn</b>op</p>',
            );
            const gh = p.firstChild.childNodes[1].childNodes[2];
            const u = gh.previousSibling;
            const span = gh.nextSibling;
            const result = getAdjacents(gh, node => node.nodeType === Node.ELEMENT_NODE);
            window.chai.expect(result).to.eql([u, gh, span]);
        });
        it('should return an empty array if the given node is not satisfying the given predicate', () => {
            const [p] = insertTestHtml(
                '<p><b>ab<i>cd<u>ef</u><a>gh</a>ij<span>kl</span>mn</i>op</b>qr</p>',
            );
            const a = p.querySelector('a');
            const result = getAdjacents(a, node => node.nodeType === Node.TEXT_NODE);
            window.chai.expect(result).to.eql([]);
        });
    });

    //------------------------------------------------------------------------------
    // Cursor management
    //------------------------------------------------------------------------------

    describe('ensureFocus', () => {
        it('should preserve the focus on the child of this.editable when executing a powerbox command even if it is enclosed in a contenteditable=false', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`
                    <div contenteditable="false"><div contenteditable="true">
                        <p>[]<br></p>
                    </div></div>
                    <p><br></p>`),
                stepFunction: async editor => {
                    const sel = document.getSelection();
                    const element = sel.anchorNode;
                    await triggerEvent(editor.editable, 'keydown', { key: '/' });
                    await insertText(editor, '/');
                    await triggerEvent(editor.editable, 'keyup', { key: '/' });
                    await insertText(editor, 'h2');
                    await triggerEvent(element, 'keyup', { key: '2' });
                    await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    const activeElement = document.activeElement;
                    setCursorStart(activeElement.lastElementChild);
                    await nextTickFrame();
                },
                contentAfter: unformat(`
                    <div contenteditable="false"><div contenteditable="true">
                        <h2>[]<br></h2>
                    </div></div>
                    <p><br></p>`),
            });
        });
        it('should preserve the focus on the child of this.editable even if it is enclosed in a contenteditable=false', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`
                    <div contenteditable="false"><div contenteditable="true">
                        <p>[]<br></p>
                    </div></div>
                    <p><br></p>`),
                stepFunction: async editor => {
                    ensureFocus(editor.editable);
                    await nextTickFrame();
                    let activeElement = document.activeElement;
                    setCursorStart(activeElement.lastElementChild);
                    await insertText(editor, 'focusWasConserved');
                    // Proof that a simple call to Element.focus would change
                    // the focus in this case.
                    editor.editable.focus();
                    await nextTickFrame();
                    activeElement = document.activeElement;
                    setCursorStart(activeElement.lastElementChild);
                    await nextTickFrame();
                },
                contentAfter: unformat(`
                    <div contenteditable="false"><div contenteditable="true">
                        <p>focusWasConserved</p>
                    </div></div>
                    <p>[]<br></p>`),
            });
        });
        it('should update the focus when the active element is not the focus target', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`
                    <div contenteditable="false"><div contenteditable="true">
                        <p>[]<br></p>
                    </div></div>
                    <div contenteditable="false"><div id="target" contenteditable="true">
                        <p><br></p>
                    </div></div>`),
                stepFunction: async editor => {
                    const element = editor.editable.querySelector('#target');
                    ensureFocus(element);
                    await nextTickFrame();
                    const activeElement = document.activeElement;
                    setCursorStart(activeElement.lastElementChild);
                    await nextTickFrame();
                },
                contentAfter: unformat(`
                    <div contenteditable="false"><div contenteditable="true">
                        <p><br></p>
                    </div></div>
                    <div contenteditable="false"><div id="target" contenteditable="true">
                        <p>[]<br></p>
                    </div></div>`),
            });
        });
    });
    describe('getNormalizedCursorPosition', () => {
        it('should move the cursor from after a <b> to within it', () => {
            const [p] = insertTestHtml('<p><b>abc</b>def</p>');
            const result = getNormalizedCursorPosition(p.lastChild, 0);
            window.chai.expect(result).to.eql([p.firstChild.firstChild, 3]);
        });
        it('should move the cursor before a non-editable element with offset === 0', () => {
            const [p] = insertTestHtml('<p><span contenteditable="false">leavemealone</span></p>');
            const result = getNormalizedCursorPosition(p.lastChild, 0);
            window.chai.expect(result).to.eql([p, 0]);
        });
        it('should move the cursor after a non-editable element with offset > 0', () => {
            const [p] = insertTestHtml('<p><span contenteditable="false">leavemealone</span></p>');
            const result = getNormalizedCursorPosition(p.lastChild, 1);
            window.chai.expect(result).to.eql([p, 1]);
        });
        it('should move the cursor after a "visibleEmpty" element', () => {
            const [p] = insertTestHtml('<p>ab<br>cd</p>');
            const result = getNormalizedCursorPosition(p.lastElementChild, 0);
            window.chai.expect(result).to.eql([p.lastChild, 0]);
        });
        it('should move the cursor before a "fake line break element"', () => {
            const [p] = insertTestHtml('<p><br></p>');
            const result = getNormalizedCursorPosition(p.lastElementChild, 0);
            window.chai.expect(result).to.eql([p, 0]);
        });
        it('should loop outside (left) a non-editable context and then find the deepest editable leaf position', () => {
            const [p] = insertTestHtml(unformat(`
                <p>
                    <a class="end">text</a>
                    <span contenteditable="false">
                        <b class="start">
                            text
                        </b>
                    </span>
                </p>
            `));
            const start = p.querySelector(".start");
            const end = p.querySelector(".end");
            const result = getNormalizedCursorPosition(start.lastChild, 0);
            window.chai.expect(result).to.eql([end.firstChild, 4]);
        });
        it('should loop outside (right) a non-editable context and then find the deepest editable leaf position', () => {
            const [p] = insertTestHtml(unformat(`
                <p>
                    <span contenteditable="false">
                        <b class="start">
                            text
                        </b>
                    </span>
                    <a class="end">text</a>
                </p>
            `));
            const start = p.querySelector(".start");
            const end = p.querySelector(".end");
            const result = getNormalizedCursorPosition(start.lastChild, 1);
            window.chai.expect(result).to.eql([end.lastChild, 0]);
        });
        it('should loop outside (left) a non-editable context and not traverse a non-editable leaf position', () => {
            const [p] = insertTestHtml(unformat(`
                <p>
                    <a contenteditable="false">leavemealone</a>
                    <span contenteditable="false">
                        <b class="start">
                            text
                        </b>
                    </span>
                </p>
            `));
            const start = p.querySelector(".start");
            const result = getNormalizedCursorPosition(start.lastChild, 0);
            window.chai.expect(result).to.eql([p, 1]);
        });
        it('should loop outside (right) a non-editable context and not traverse a non-editable leaf position', () => {
            const [p] = insertTestHtml(unformat(`
                <p>
                    <span contenteditable="false">
                        <b class="start">
                            text
                        </b>
                    </span>
                    <a contenteditable="false">leavemealone</a>
                </p>
            `));
            const start = p.querySelector(".start");
            const result = getNormalizedCursorPosition(start.lastChild, 1);
            window.chai.expect(result).to.eql([p, 1]);
        });
    });
    describe('setCursor', () => {
        describe('collapsed', () => {
            it('should collapse the cursor at the beginning of an element', () => {
                const [p] = insertTestHtml('<p>abc</p>');
                const result = setSelection(p.firstChild, 0);
                window.chai.expect(result).to.eql([p.firstChild, 0, p.firstChild, 0]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([p.firstChild, 0, p.firstChild, 0]);
            });
            it('should collapse the cursor within an element', () => {
                const [p] = insertTestHtml('<p>abcd</p>');
                const result = setSelection(p.firstChild, 2);
                window.chai.expect(result).to.eql([p.firstChild, 2, p.firstChild, 2]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([p.firstChild, 2, p.firstChild, 2]);
            });
            it('should collapse the cursor at the end of an element', () => {
                const [p] = insertTestHtml('<p>abc</p>');
                const result = setSelection(p.firstChild, 3);
                window.chai.expect(result).to.eql([p.firstChild, 3, p.firstChild, 3]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([p.firstChild, 3, p.firstChild, 3]);
            });
            it('should collapse the cursor before a nested inline element', () => {
                const [p] = insertTestHtml('<p>ab<span>cd<b>ef</b>gh</span>ij</p>');
                const cd = p.childNodes[1].firstChild;
                const result = setSelection(cd, 2);
                window.chai.expect(result).to.eql([cd, 2, cd, 2]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([cd, 2, cd, 2]);
            });
            it('should collapse the cursor at the beginning of a nested inline element', () => {
                const [p] = insertTestHtml('<p>ab<span>cd<b>ef</b>gh</span>ij</p>');
                const ef = p.childNodes[1].childNodes[1].firstChild;
                const result = setSelection(ef, 0);
                window.chai.expect(result).to.eql([ef, 0, ef, 0]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([ef, 0, ef, 0]);
            });
            it('should collapse the cursor within a nested inline element', () => {
                const [p] = insertTestHtml('<p>ab<span>cd<b>efgh</b>ij</span>kl</p>');
                const efgh = p.childNodes[1].childNodes[1].firstChild;
                const result = setSelection(efgh, 2);
                window.chai.expect(result).to.eql([efgh, 2, efgh, 2]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([efgh, 2, efgh, 2]);
            });
            it('should collapse the cursor at the end of a nested inline element', () => {
                const [p] = insertTestHtml('<p>ab<span>cd<b>ef</b>gh</span>ij</p>');
                const ef = p.childNodes[1].childNodes[1].firstChild;
                const result = setSelection(ef, 2);
                window.chai.expect(result).to.eql([ef, 2, ef, 2]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([ef, 2, ef, 2]);
            });
            it('should collapse the cursor after a nested inline element', () => {
                const [p] = insertTestHtml('<p>ab<span>cd<b>ef</b>gh</span>ij</p>');
                const ef = p.childNodes[1].childNodes[1].firstChild;
                const gh = p.childNodes[1].lastChild;
                const result = setSelection(gh, 0);
                window.chai.expect(result).to.eql([ef, 2, ef, 2]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([ef, 2, ef, 2]);

                const nonNormalizedResult = setSelection(gh, 0, gh, 0, false);
                window.chai.expect(nonNormalizedResult).to.eql([gh, 0, gh, 0]);
                const sel = document.getSelection();
                window.chai
                    .expect([sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset])
                    .to.eql([gh, 0, gh, 0]);
            });
        });
        describe('forward', () => {
            it('should select the contents of an element', () => {
                const [p] = insertTestHtml('<p>abc</p>');
                const result = setSelection(p.firstChild, 0, p.firstChild, 3);
                window.chai.expect(result).to.eql([p.firstChild, 0, p.firstChild, 3]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([p.firstChild, 0, p.firstChild, 3]);
            });
            it('should make a complex selection', () => {
                const [p1, p2] = insertTestHtml(
                    '<p>ab<span>cd<b>ef</b>gh</span>ij</p><p>kl<span>mn<b>op</b>qr</span>st</p>',
                );
                const ef = p1.childNodes[1].childNodes[1].firstChild;
                const qr = p2.childNodes[1].childNodes[2];
                const st = p2.childNodes[2];
                const result = setSelection(ef, 1, st, 0);
                window.chai.expect(result).to.eql([ef, 1, qr, 2]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([ef, 1, qr, 2]);

                const nonNormalizedResult = setSelection(ef, 1, st, 0, false);
                window.chai.expect(nonNormalizedResult).to.eql([ef, 1, st, 0]);
                const sel = document.getSelection();
                window.chai
                    .expect([sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset])
                    .to.eql([ef, 1, st, 0]);
            });
        });
        describe('backward', () => {
            it('should select the contents of an element', () => {
                const [p] = insertTestHtml('<p>abc</p>');
                const result = setSelection(p.firstChild, 3, p.firstChild, 0);
                window.chai.expect(result).to.eql([p.firstChild, 3, p.firstChild, 0]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([p.firstChild, 3, p.firstChild, 0]);
            });
            it('should make a complex selection', () => {
                const [p1, p2] = insertTestHtml(
                    '<p>ab<span>cd<b>ef</b>gh</span>ij</p><p>kl<span>mn<b>op</b>qr</span>st</p>',
                );
                const ef = p1.childNodes[1].childNodes[1].firstChild;
                const qr = p2.childNodes[1].childNodes[2];
                const st = p2.childNodes[2];
                const result = setSelection(st, 0, ef, 1);
                window.chai.expect(result).to.eql([qr, 2, ef, 1]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([qr, 2, ef, 1]);

                const nonNormalizedResult = setSelection(st, 0, ef, 1, false);
                window.chai.expect(nonNormalizedResult).to.eql([st, 0, ef, 1]);
                const sel = document.getSelection();
                window.chai
                    .expect([sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset])
                    .to.eql([st, 0, ef, 1]);
            });
        });
    });
    describe('setCursorStart', () => {
        it('should collapse the cursor at the beginning of an element', () => {
            const [p] = insertTestHtml('<p>abc</p>');
            const result = setCursorStart(p);
            window.chai.expect(result).to.eql([p.firstChild, 0, p.firstChild, 0]);
            const { anchorNode, anchorOffset, focusNode, focusOffset } = document.getSelection();
            window.chai
                .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                .to.eql([p.firstChild, 0, p.firstChild, 0]);
        });
        it('should collapse the cursor at the beginning of a nested inline element', () => {
            const [p] = insertTestHtml('<p>ab<span>cd<b>ef</b>gh</span>ij</p>');
            const b = p.childNodes[1].childNodes[1];
            const ef = b.firstChild;
            const result = setCursorStart(b);
            window.chai.expect(result).to.eql([ef, 0, ef, 0]);
            const { anchorNode, anchorOffset, focusNode, focusOffset } = document.getSelection();
            window.chai
                .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                .to.eql([ef, 0, ef, 0]);
        });
        it('should collapse the cursor after a nested inline element', () => {
            const [p] = insertTestHtml('<p>ab<span>cd<b>ef</b>gh</span>ij</p>');
            const ef = p.childNodes[1].childNodes[1].firstChild;
            const gh = p.childNodes[1].lastChild;
            const result = setCursorStart(gh);
            window.chai.expect(result).to.eql([ef, 2, ef, 2]);
            const { anchorNode, anchorOffset, focusNode, focusOffset } = document.getSelection();
            window.chai
                .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                .to.eql([ef, 2, ef, 2]);

            const nonNormalizedResult = setCursorStart(gh, false);
            window.chai.expect(nonNormalizedResult).to.eql([gh, 0, gh, 0]);
            const sel = document.getSelection();
            window.chai
                .expect([sel.anchorNode, sel.anchorOffset, sel.focusNode, sel.focusOffset])
                .to.eql([gh, 0, gh, 0]);
        });
    });
    describe('setCursorEnd', () => {
        it('should collapse the cursor at the end of an element', () => {
            const [p] = insertTestHtml('<p>abc</p>');
            const result = setCursorEnd(p);
            window.chai.expect(result).to.eql([p.firstChild, 3, p.firstChild, 3]);
            const { anchorNode, anchorOffset, focusNode, focusOffset } = document.getSelection();
            window.chai
                .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                .to.eql([p.firstChild, 3, p.firstChild, 3]);
        });
        it('should collapse the cursor before a nested inline element', () => {
            const [p] = insertTestHtml('<p>ab<span>cd<b>ef</b>gh</span>ij</p>');
            const cd = p.childNodes[1].firstChild;
            const result = setCursorEnd(cd);
            window.chai.expect(result).to.eql([cd, 2, cd, 2]);
            const { anchorNode, anchorOffset, focusNode, focusOffset } = document.getSelection();
            window.chai
                .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                .to.eql([cd, 2, cd, 2]);
        });
        it('should collapse the cursor at the end of a nested inline element', () => {
            const [p] = insertTestHtml('<p>ab<span>cd<b>ef</b>gh</span>ij</p>');
            const b = p.childNodes[1].childNodes[1];
            const ef = b.firstChild;
            const result = setCursorEnd(b);
            window.chai.expect(result).to.eql([ef, 2, ef, 2]);
            const { anchorNode, anchorOffset, focusNode, focusOffset } = document.getSelection();
            window.chai
                .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                .to.eql([ef, 2, ef, 2]);
        });
    });
    describe('getCursorDirection', () => {
        it('should identify a forward selection', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[bc]d</p>',
                stepFunction: editor => {
                    const { anchorNode, anchorOffset, focusNode, focusOffset } =
                        editor.document.getSelection();
                    window.chai
                        .expect(
                            getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset),
                        )
                        .to.equal(DIRECTIONS.RIGHT);
                },
            });
        });
        it('should identify a backward selection', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a]bc[d</p>',
                stepFunction: editor => {
                    const { anchorNode, anchorOffset, focusNode, focusOffset } =
                        editor.document.getSelection();
                    window.chai
                        .expect(
                            getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset),
                        )
                        .to.equal(DIRECTIONS.LEFT);
                },
            });
        });
        it('should identify a collapsed selection', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]cd</p>',
                stepFunction: editor => {
                    const { anchorNode, anchorOffset, focusNode, focusOffset } =
                        editor.document.getSelection();
                    window.chai
                        .expect(
                            getCursorDirection(anchorNode, anchorOffset, focusNode, focusOffset),
                        )
                        .to.equal(false);
                },
            });
        });
    });
    describe('getTraversedNodes', () => {
        it('should return the text node in which the range is collapsed', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]cd</p>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const abcd = editable.firstChild.firstChild;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([abcd]);
                },
            });
        });
        it('should find that a the range traverses the next paragraph as well', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[cd</p><p>ef]gh</p>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const abcd = editable.firstChild.firstChild;
                    const p2 = editable.childNodes[1];
                    const efgh = p2.firstChild;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([abcd, p2, efgh]);
                },
            });
        });
        it('should find all traversed nodes in nested range', async () => {
            await testEditor(BasicEditor, {
                contentBefore:
                    '<p><span class="a">ab[</span>cd</p><div><p><span class="b"><b>e</b><i>f]g</i>h</span></p></div>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const ab = editable.firstChild.firstChild.firstChild;
                    const cd = editable.firstChild.lastChild;
                    const div = editable.lastChild;
                    const p2 = div.firstChild;
                    const span2 = p2.firstChild;
                    const b = span2.firstChild;
                    const e = b.firstChild;
                    const i = b.nextSibling;
                    const fg = i.firstChild;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([ab, cd, div, p2, span2, b, e, i, fg]);
                },
            });
        });
        it('selection does not have an edge with a br element', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '[<p>ab</p><p>cd<br></p>]',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const ab = editable.firstChild.firstChild;
                    const p2 = editable.lastChild;
                    const cd = p2.firstChild;
                    const br = p2.lastChild;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([ab, p2, cd, br]);
                },
            });
        });
        it('selection ends before br element at start of p element', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '[<p>ab</p><p>]<br>cd<br></p>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const ab = editable.firstChild.firstChild;
                    const p2 = editable.firstChild.nextSibling;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([ab, p2]);
                },
            });
        });
        it('selection ends before a br in middle of p element', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '[<p>ab</p><p><br>cd]<br>ef<br></p>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const ab = editable.firstChild.firstChild;
                    const p2 = editable.lastChild;
                    const firstBr = p2.firstChild;
                    const cd = firstBr.nextSibling;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([ab, p2, firstBr, cd]);
                },
            });
        });
        it('selection end after a br in middle of p elemnt', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '[<p>ab</p><p><br>cd<br>]ef<br></p>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const ab = editable.firstChild.firstChild;
                    const p2 = editable.lastChild;
                    const br1 = p2.firstChild;
                    const cd = br1.nextSibling;
                    const br2 = cd.nextSibling;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([ab, p2, br1, cd, br2]);
                },
            });
        });
        it('selection ends after a br at end of p elemnt', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '[<p>ab</p><p><br>cd<br>]</p>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const ab = editable.firstChild.firstChild;
                    const p2 = editable.lastChild;
                    const br1 = p2.firstChild;
                    const cd = br1.nextSibling;
                    const br2 = cd.nextSibling;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([ab, p2, br1, cd, br2]);
                },
            });
        });
        it('selection ends between 2 br elements', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '[<p>ab</p><p>cd<br>]<br>ef</p>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const ab = editable.firstChild.firstChild;
                    const p2 =  editable.firstChild.nextSibling;
                    const cd = p2.firstChild;
                    const br1 = cd.nextSibling;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([ab, p2, cd, br1]);
                },
            });
        });
        it('selection starts before a br in middle of p element', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[<br>cd</p><p>ef</p>]',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const ab = editable.firstChild.firstChild;
                    const br = ab.nextSibling;
                    const cd = br.nextSibling;
                    const p2 = editable.lastChild;
                    const ef = p2.firstChild;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([br, cd, p2, ef]);
                },
            });
        });
        it('selection starts before a br in start of p element', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[ab<br>cd</p><p>ef</p>]',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const ab = editable.firstChild.firstChild;
                    const br = ab.nextSibling;
                    const cd = br.nextSibling;
                    const p2 = editable.lastChild;
                    const ef = p2.firstChild;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([ab, br, cd, p2, ef]);
                },
            });
        });
        it('selection starts after a br at end of p element', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab<br>[</p><p>cd</p>]',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const p2 = editable.lastChild;
                    const cd = p2.firstChild;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([p2, cd]);
                },
            });
        });
        it('selection starts after a br in middle of p element', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab<br>[cd</p><p>ef</p>]',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const ab = editable.firstChild.firstChild;
                    const br = ab.nextSibling;
                    const cd = br.nextSibling;
                    const p2 = editable.lastChild;
                    const ef = p2.firstChild;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([cd, p2, ef]);
                },
            });
        });
        it('selection starts between 2 br elements', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab<br>[<br>cd</p><p>ef</p>]',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const ab = editable.firstChild.firstChild;
                    const br1 = ab.nextSibling;
                    const br2 = br1.nextSibling;
                    const cd = br2.nextSibling;
                    const p2 =  editable.firstChild.nextSibling;
                    const ef = p2.firstChild;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([br2, cd, p2, ef]);
                },
            });
        });
        it("selection within table cells 1", async () => {
            await testEditor(BasicEditor, {
                contentBefore:
                    "<table><tbody><tr><td>abcd[e</td><td>f]g</td></tr></tbody></table>",
                stepFunction: editor => {
                    const editable = editor.editable;
                    const tr = editable.firstChild.firstChild.firstChild;
                    const td1 = tr.firstChild;
                    const abcde = td1.firstChild;
                    const td2 = td1.nextSibling;
                    const fg = td2.firstChild;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([td1, abcde, td2, fg]);
                },
            });
        });
        it("selection within table cells 2", async () => {
            await testEditor(BasicEditor, {
                contentBefore:
                    "<table><tbody><tr><td>abcd<br>[<br>e</td><td>f]g</td></tr></tbody></table>",
                stepFunction: editor => {
                    const editable = editor.editable;
                    const tr = editable.firstChild.firstChild.firstChild;
                    const td1 = tr.firstChild;
                    const abcd = td1.firstChild;
                    const br1 = abcd.nextSibling;
                    const br2 = br1.nextSibling;
                    const e = br2.nextSibling;
                    const td2 = td1.nextSibling;
                    const fg = td2.firstChild;
                    const result = getTraversedNodes(editable);
                    window.chai.expect(result).to.eql([td1, abcd, br1, br2, e, td2, fg]);
                },
            });
        });
    });
    describe('getSelectedNodes', () => {
        it('should return nothing if the range is collapsed', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]cd</p>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const result = getSelectedNodes(editable);
                    window.chai.expect(result).to.eql([]);
                },
                contentAfter: '<p>ab[]cd</p>',
            });
        });
        it('should find that no node is fully selected', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[c]d</p>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const result = getSelectedNodes(editable);
                    window.chai.expect(result).to.eql([]);
                },
            });
        });
        it('should find that no node is fully selected, across blocks', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[cd</p><p>ef]gh</p>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const result = getSelectedNodes(editable);
                    window.chai.expect(result).to.eql([]);
                },
            });
        });
        it('should find that a text node is fully selected', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><span class="a">ab</span>[cd]</p>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const result = getSelectedNodes(editable);
                    const cd = editable.firstChild.lastChild;
                    window.chai.expect(result).to.eql([cd]);
                },
            });
        });
        it('should find that a block is fully selected', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[ab</p><p>cd</p><p>ef]gh</p>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const result = getSelectedNodes(editable);
                    const ab = editable.firstChild.firstChild;
                    const p2 = editable.childNodes[1];
                    const cd = p2.firstChild;
                    window.chai.expect(result).to.eql([ab, p2, cd]);
                },
            });
        });
        it('should find all selected nodes in nested range', async () => {
            await testEditor(BasicEditor, {
                contentBefore:
                    '<p><span class="a">ab[</span>cd</p><div><p><span class="b"><b>e</b><i>f]g</i>h</span></p></div>',
                stepFunction: editor => {
                    const editable = editor.editable;
                    const cd = editable.firstChild.lastChild;
                    const b = editable.lastChild.firstChild.firstChild.firstChild;
                    const e = b.firstChild;
                    const result = getSelectedNodes(editable);
                    window.chai.expect(result).to.eql([cd, b, e]);
                },
            });
        });
    });
    describe('getDeepRange', () => {
        describe('collapsed', () => {
            it('should collapse the cursor at the beginning of an element', () => {
                const [p] = insertTestHtml(
                    `<p>
                        <span><b><i><u>abc</u></i></b></span>
                    </p>`,
                );
                const abc = p.childNodes[1].firstChild.firstChild.firstChild.firstChild;
                const range = document.createRange();
                range.setStart(p, 0);
                range.setEnd(p, 0);
                const result = getDeepRange(p.parentElement, { range, select: true });
                const { startContainer, startOffset, endContainer, endOffset } = result;
                window.chai
                    .expect([startContainer, startOffset, endContainer, endOffset])
                    .to.eql([abc, 0, abc, 0]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([abc, 0, abc, 0]);
            });
            it('should collapse the cursor at the end of a nested inline element', () => {
                const [p] = insertTestHtml(
                    `<p>
                        <span><b><i><u>abc</u></i></b></span>
                    </p>`,
                );
                const abc = p.childNodes[1].firstChild.firstChild.firstChild.firstChild;
                const range = document.createRange();
                range.setStart(p, 2);
                range.setEnd(p, 2);
                const result = getDeepRange(p.parentElement, { range, select: true });
                const { startContainer, startOffset, endContainer, endOffset } = result;
                window.chai
                    .expect([startContainer, startOffset, endContainer, endOffset])
                    .to.eql([abc, 3, abc, 3]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([abc, 3, abc, 3]);
            });
        });
        describe('forward', () => {
            it('should select the contents of an element', () => {
                const [p] = insertTestHtml(
                    `<p>
                        <span><b><i><u>abc</u></i></b></span>
                    </p>`,
                );
                const abc = p.childNodes[1].firstChild.firstChild.firstChild.firstChild;
                const range = document.createRange();
                range.setStart(p, 0);
                range.setEnd(p, 2);
                const result = getDeepRange(p.parentElement, { range, select: true });
                const { startContainer, startOffset, endContainer, endOffset } = result;
                window.chai
                    .expect([startContainer, startOffset, endContainer, endOffset])
                    .to.eql([abc, 0, abc, 3]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([abc, 0, abc, 3]);
            });
            it('should make a complex selection', () => {
                const [p1, p2] = insertTestHtml(
                    `<p>
                        ab<span>cd<b>ef</b>gh</span>ij
                    </p><p>
                        kl<span>mn<b>op</b>qr</span>st
                    </p>`,
                );
                const span1 = p1.childNodes[1];
                const ef = span1.querySelector('b').firstChild;
                const st = p2.childNodes[2];
                const range = document.createRange();
                range.setStart(span1, 1);
                range.setEnd(p2, 2);
                const result = getDeepRange(p1.parentElement, { range, select: true });
                const { startContainer, startOffset, endContainer, endOffset } = result;
                const expect = [startContainer, startOffset, endContainer, endOffset];
                const eql = [ef, 0, st, 0];
                window.chai.expect(expect).to.eql(eql);
            });
            it('should correct a triple click', () => {
                const [p1, p2] = insertTestHtml('<p>abc def ghi</p><p>jkl mno pqr</p>');
                const range = document.createRange();
                range.setStart(p1, 0);
                range.setEnd(p2, 0);
                const result = getDeepRange(p1.parentElement, {
                    range,
                    select: true,
                    correctTripleClick: true,
                });
                const { startContainer, startOffset, endContainer, endOffset } = result;
                window.chai
                    .expect([startContainer, startOffset, endContainer, endOffset])
                    .to.eql([p1.firstChild, 0, p1.firstChild, 11]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([p1.firstChild, 0, p1.firstChild, 11]);
            });
            it('should not correct a triple click on collapse', () => {
                const [p1, div] = insertTestHtml('<p>abc def ghi</p><div><p>jkl mno pqr</p></div>');
                const p2 = div.firstChild;
                const range = document.createRange();
                range.setStart(p2, 0);
                range.setEnd(p2, 0);
                const result = getDeepRange(p1.parentElement, {
                    range,
                    select: true,
                    correctTripleClick: true,
                });
                const { startContainer, startOffset, endContainer, endOffset } = result;
                window.chai
                    .expect([startContainer, startOffset, endContainer, endOffset])
                    .to.eql([p2.firstChild, 0, p2.firstChild, 0]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([p2.firstChild, 0, p2.firstChild, 0]);
            });
            it('should limit the selection to the title text (nested)', () => {
                const [p] = insertTestHtml(
                    `<p>
                        <span>
                            <font>title</font>
                        </span>
                    </p>`,
                );
                const span = p.childNodes[1];
                const whiteBeforeFont = span.childNodes[0];
                const title = span.childNodes[1].firstChild;
                const whiteAfterFont = span.childNodes[2];
                const range = document.createRange();
                range.setStart(whiteBeforeFont, 0);
                range.setEnd(whiteAfterFont, 10);
                const result = getDeepRange(p.parentElement, { range, select: true });
                const { startContainer, startOffset, endContainer, endOffset } = result;
                window.chai
                    .expect([startContainer, startOffset, endContainer, endOffset])
                    .to.eql([title, 0, title, 5]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([title, 0, title, 5]);
            });
            it('should not limit the selection to the title text within p siblings', () => {
                const [p0, p1, p2] = insertTestHtml(
                    `<p><br/></p><p>
                        <font>title</font>
                    </p><p><br/></p>`,
                );
                const range = document.createRange();
                range.setStart(p0, 0);
                range.setEnd(p2, 0);
                const result = getDeepRange(p1.parentElement, { range, select: true });
                const { startContainer, startOffset, endContainer, endOffset } = result;
                window.chai
                    .expect([startContainer, startOffset, endContainer, endOffset])
                    .to.eql([p0, 0, p2, 0]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([p0, 0, p2, 0]);
            });
        });
        describe('backward', () => {
            it('should select the contents of an element', () => {
                const [p] = insertTestHtml(
                    `<p>
                        <span><b><i><u>abc</u></i></b></span>
                    </p>`,
                );
                const abc = p.childNodes[1].firstChild.firstChild.firstChild.firstChild;
                setSelection(p, 2, p, 0, false);
                const result = getDeepRange(p.parentElement, { select: true });
                const { startContainer, startOffset, endContainer, endOffset } = result;
                window.chai
                    .expect([startContainer, startOffset, endContainer, endOffset])
                    .to.eql([abc, 0, abc, 3]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([abc, 3, abc, 0]);
            });
            it('should make a complex selection', () => {
                const [p1, p2] = insertTestHtml(
                    `<p>
                        ab<span>cd<b>ef</b>gh</span>ij
                    </p><p>
                        kl<span>mn<b>op</b>qr</span>st
                    </p>`,
                );
                const span1 = p1.childNodes[1];
                const ef = span1.childNodes[1].firstChild;
                const st = p2.childNodes[2];
                setSelection(p2, 2, span1, 1, false);
                const result = getDeepRange(p1.parentElement, { select: true });
                const { startContainer, startOffset, endContainer, endOffset } = result;
                window.chai
                    .expect([startContainer, startOffset, endContainer, endOffset])
                    .to.eql([ef, 0, st, 0]);
                const { anchorNode, anchorOffset, focusNode, focusOffset } =
                    document.getSelection();
                window.chai
                    .expect([anchorNode, anchorOffset, focusNode, focusOffset])
                    .to.eql([st, 0, ef, 0]);
            });
        });
    });
    // TODO:
    // - getDeepestPosition
    // - getCursors
    // - preserveCursor

    //------------------------------------------------------------------------------
    // DOM Info utils
    //------------------------------------------------------------------------------

    describe('isVisible', () => {
        describe('textNode', () => {
            it('should identify an invisible textnode at the beginning of a paragraph before an inline node', () => {
                const [p] = insertTestHtml('<p> <i>a</i></p>');
                const result = isVisible(p.firstChild);
                window.chai.expect(result).not.to.be.ok;
            });
            it('should identify invisible string space at the end of a paragraph after an inline node', () => {
                const [p] = insertTestHtml('<p><i>a</i> </p>');
                const result = isVisible(p.lastChild);
                window.chai.expect(result).not.to.be.ok;
            });
            it('should identify a single visible space in an inline node in the middle of a paragraph', () => {
                const [p] = insertTestHtml('<p>a<i> </i>b</p>');
                const result = isVisible(p.querySelector('i').firstChild);
                window.chai.expect(result).to.be.ok;
            });
            it('should identify a visible string with only one visible space in an inline node in the middle of a paragraph', () => {
                const [p] = insertTestHtml('<p>a<i>   </i>b</p>');
                const result = isVisible(p.querySelector('i').firstChild);
                window.chai.expect(result).to.be.ok;
            });
            it('should identify a visible space in the middle of a paragraph', () => {
                const [p] = insertTestHtml('<p></p>');
                // insert 'a b' as three separate text node inside p
                const textNodes = 'a b'.split('').map(char => {
                    const textNode = document.createTextNode(char);
                    p.appendChild(textNode);
                    return textNode;
                });
                const result = isVisible(textNodes[1]);
                window.chai.expect(result).to.be.ok;
            });
            it('should identify a visible string space in the middle of a paragraph', () => {
                const [p] = insertTestHtml('<p></p>');
                // inserts 'a', '   ' and  'b' as 3 separate text nodes inside p
                const textNodes = ['a', '   ', 'b'].map(char => {
                    const textNode = document.createTextNode(char);
                    p.appendChild(textNode);
                    return textNode;
                });
                const result = isVisible(textNodes[1]);
                window.chai.expect(result).to.be.ok;
            });
            it('should identify the first space in a series of spaces as in the middle of a paragraph as visible', () => {
                const [p] = insertTestHtml('<p></p>');
                // inserts 'a   b' as 5 separate text nodes inside p
                const textNodes = 'a   b'.split('').map(char => {
                    const textNode = document.createTextNode(char);
                    p.appendChild(textNode);
                    return textNode;
                });
                const result = isVisible(textNodes[1]);
                window.chai.expect(result).to.be.ok;
            });
            it('should identify the second space in a series of spaces in the middle of a paragraph as invisible', () => {
                const [p] = insertTestHtml('<p></p>');
                // inserts 'a   b' as 5 separate text nodes inside p
                const textNodes = 'a   b'.split('').map(char => {
                    const textNode = document.createTextNode(char);
                    p.appendChild(textNode);
                    return textNode;
                });
                const result = isVisible(textNodes[2]);
                window.chai.expect(result).not.to.be.ok;
            });
            it('should identify empty text node as invisible', () => {
                const [p] = insertTestHtml('<p></p>');
                // inserts 'a   b' as 5 separate text nodes inside p
                const textNode = document.createTextNode('');
                p.appendChild(textNode);
                const result = isVisible(textNode);
                window.chai.expect(result).not.to.be.ok;
            });
            it('should identify a space between to visible char in inline nodes as visible', () => {
                const [p] = insertTestHtml('<p><i>a</i> <i>b</i></p>');
                const textNode = p.firstChild.nextSibling;

                const result = isVisible(textNode);

                window.chai.expect(result).to.be.ok;
                cleanTestHtml();
            });
        });
    });

    //--------------------------------------------------------------------------
    // DOM Modification
    //--------------------------------------------------------------------------

    describe('splitAroundUntil', () => {
        it('should split a slice of text from its inline ancestry', () => {
            const [p] = insertTestHtml('<p>a<font>b<span>cde</span>f</font>g</p>');
            const cde = p.childNodes[1].childNodes[1].firstChild;
            // We want to test with "cde" being three separate text nodes.
            splitTextNode(cde, 2);
            const cd = cde.previousSibling;
            splitTextNode(cd, 1);
            const d = cd;
            const result = splitAroundUntil(d, p.childNodes[1]);
            window.chai.expect(result.tagName === 'FONT').to.be.ok;
            window.chai.expect(p.outerHTML).to.eql(
                '<p>a<font>b<span>c</span></font><font><span>d</span></font><font><span>e</span>f</font>g</p>'
            );
        });
        it('should split a slice of text from its inline ancestry', () => {
            const [p] = insertTestHtml('<p>a<font>b<span>cdefg</span>h</font>i</p>');
            const cdefg = p.childNodes[1].childNodes[1].firstChild;
            // We want to test with "cdefg" being five separate text nodes.
            splitTextNode(cdefg, 4);
            const cdef = cdefg.previousSibling;
            splitTextNode(cdef, 3);
            const cde = cdef.previousSibling;
            splitTextNode(cde, 2);
            const cd = cde.previousSibling;
            splitTextNode(cd, 1);
            const d = cd;
            const result = splitAroundUntil([d, d.nextSibling.nextSibling], p.childNodes[1]);
            window.chai.expect(result.tagName === 'FONT').to.be.ok;
            window.chai.expect(p.outerHTML).to.eql(
                '<p>a<font>b<span>c</span></font><font><span>def</span></font><font><span>g</span>h</font>i</p>'
            );
        });
        it('should split from a textNode that has no siblings', () => {
            const [p] = insertTestHtml('<p>a<font>b<span>cde</span>f</font>g</p>');
            const font = p.querySelector('font');
            const cde = p.querySelector('span').firstChild;
            const result = splitAroundUntil(cde, font);
            window.chai.expect(result.tagName === 'FONT' && result !== font).to.be.ok;
            window.chai.expect(p.outerHTML).to.eql('<p>a<font>b</font><font><span>cde</span></font><font>f</font>g</p>');
        });
        it('should not do anything (nothing to split)', () => {
            const [p] = insertTestHtml('<p>a<font><span>bcd</span></font>e</p>');
            const bcd = p.querySelector('span').firstChild;
            const result = splitAroundUntil(bcd, p.childNodes[1]);
            window.chai.expect(result === p.childNodes[1]).to.be.ok;
            window.chai.expect(p.outerHTML).to.eql('<p>a<font><span>bcd</span></font>e</p>');
        });

    });

    describe('CleanUp Html', () => {
        it('should not affect future tests => clean', () => {
            const res = cleanTestHtml();
            window.chai.expect(res).to.be.true;
        });
    });

    //------------------------------------------------------------------------------
    // Prepare / Save / Restore state utilities
    //------------------------------------------------------------------------------

    describe('State preservation utilities', () => {
        describe('getState', () => {
            it('should recognize invisible space to the right', () => {
                // We'll be looking to the right while standing at `a[] `.
                const [p] = insertTestHtml('<p>a </p>');
                splitTextNode(p.firstChild, 1); // "a"" "
                window.chai.expect(p.childNodes.length).to.eql(2);
                const position = [p, 1]; // `<p>"a"[]" "</p>`
                window.chai.expect(getState(...position, DIRECTIONS.RIGHT)).to.eql({
                    // We look to the right of "a" (`a[] `):
                    node: p.firstChild, // "a"
                    direction: DIRECTIONS.RIGHT,
                    // The browser strips the space away so we ignore it and see
                    // `</p>`: the closing tag from the inside.
                    cType: CTYPES.BLOCK_INSIDE,
                });
            });
            it('should recognize invisible space to the right (among consecutive space within content)', () => {
                // We'll be looking to the right while standing at `a [] `. The
                // first space is visible, the rest isn't.
                const [p] = insertTestHtml('<p>a  b</p>');
                splitTextNode(p.firstChild, 2); // "a "" b"
                window.chai.expect(p.childNodes.length).to.eql(2);
                const position = [p, 1]; // `<p>"a "[]" b"</p>`
                window.chai.expect(getState(...position, DIRECTIONS.RIGHT)).to.eql({
                    // We look to the right of "a " (`a []`):
                    node: p.firstChild, // "a "
                    direction: DIRECTIONS.RIGHT,
                    // The browser strips the space away so we ignore it and see
                    // "b": visible content.
                    cType: CTYPES.CONTENT,
                });
            });
            it('should recognize visible space to the left (followed by consecutive space within content)', () => {
                // We'll be looking to the left while standing at `[] b`. The
                // first space is visible, the rest isn't.
                const [p] = insertTestHtml('<p>a  b</p>');
                splitTextNode(p.firstChild, 2); // "a "" b"
                window.chai.expect(p.childNodes.length).to.eql(2);
                const position = [p, 1]; // `<p>"a "[]" b"</p>`
                window.chai.expect(getState(...position, DIRECTIONS.LEFT)).to.eql({
                    // We look to the left of " b" (`[] b`):
                    node: p.lastChild, // "a"
                    direction: DIRECTIONS.LEFT,
                    // Left of " b" we see visible space that we should
                    // preserve.
                    cType: CTYPES.SPACE,
                });
            });
            it('should recognize invisible space to the left (nothing after)', () => {
                // We'll be looking to the left while standing at ` [] `.
                const [p] = insertTestHtml('<p> </p>');
                p.append(document.createTextNode('')); // " """
                window.chai.expect(getState(p, 1, DIRECTIONS.LEFT)).to.eql({
                    // We look to the left of " " (` []`):
                    node: p.lastChild, // ""
                    direction: DIRECTIONS.LEFT,
                    // The browser strips the space away so we ignore it and see
                    // `<p>`: the opening tag from the inside.
                    cType: CTYPES.BLOCK_INSIDE,
                });
            });
            it('should recognize invisible space to the left (more space after)', () => {
                // We'll be looking to the left while standing at ` [] `.
                const [p] = insertTestHtml('<p>    </p>');
                splitTextNode(p.firstChild, 1); // " ""   "
                window.chai.expect(getState(p, 1, DIRECTIONS.LEFT)).to.eql({
                    // We look to the left of "   " (` []   `):
                    node: p.lastChild, // "   ".
                    direction: DIRECTIONS.LEFT,
                    // The browser strips the space away so we ignore it and see
                    // `<p>`: the opening tag from the inside.
                    cType: CTYPES.BLOCK_INSIDE,
                });
            });
            it('should recognize invisible space to the left (br after)', () => {
                // We'll be looking to the left while standing at ` [] `.
                const [p] = insertTestHtml('<p> <br></p>');
                window.chai.expect(getState(p, 1, DIRECTIONS.LEFT)).to.eql({
                    // We look to the left of the br element (` []<br>`):
                    node: p.lastChild, // `<br>`.
                    direction: DIRECTIONS.LEFT,
                    // The browser strips the space away so we ignore it and see
                    // `<p>`: the opening tag from the inside.
                    cType: CTYPES.BLOCK_INSIDE,
                });
            });
        });
        describe('restoreState', () => {
            it('should restore invisible space to the left (looking right)', () => {
                // We'll be restoring the state of "a []" in `<p>a </p>`.
                const [p] = insertTestHtml('<p>a b</p>');
                splitTextNode(p.firstChild, 2); // "a ""b"
                const rule = restoreState({
                    // We look to the right of "a " (`a []b`) to see if we need
                    // to preserve the space at the end of "a ":
                    node: p.firstChild, // "a "
                    direction: DIRECTIONS.RIGHT,
                    // The DOM used to be `<p>a </p>` so to the right of "a " we
                    // used to see `</p>`: the closing tag from the inside.
                    cType: CTYPES.BLOCK_INSIDE,
                });
                // Now looking to the right of "a " we see "b", which is content
                // and makes the formerly invisible space visible. We should get
                // back a rule that will enforce the invisibility of the space.
                window.chai.expect(rule.spaceVisibility).to.be.false;
            });
            it('should restore visible space to the left (looking right) (among consecutive space within content)', () => {
                // We'll be restoring the state of "a []" in `<p>a  b</p>`.
                // The first space is visible, the rest isn't.
                const [p] = insertTestHtml('<p>a  </p>');
                splitTextNode(p.firstChild, 2); // "a "" "
                const rule = restoreState({
                    // We look to the right of "a " (`a []`) to see if we need
                    // to preserve the space at the end of "a ":
                    node: p.firstChild, // "a "
                    direction: DIRECTIONS.RIGHT,
                    // The DOM used to be `<p>a  b</p>` so to the right of "a " we
                    // used to see "b" which is visible content.
                    cType: CTYPES.CONTENT,
                });
                // Now looking to the right of "a " we see `</p>`: the closing
                // tag, from the inside. This makes the formerly visible space
                // invisible. We should get back a rule that will enforce the
                // visibility of the space.
                window.chai.expect(rule.spaceVisibility).to.be.true;
            });
            it('should restore visible space to the right (looking left) (followed by consecutive space within content)', () => {
                // We'll be restoring the state of "[] b" in `<p>a  b</p>`.
                // The first space is visible, the rest isn't.
                const [p] = insertTestHtml('<p>a  </p>');
                splitTextNode(p.firstChild, 2); // "a "" "
                const rule = restoreState({
                    // We look to the left of " " (`[] `) to see if we need
                    // to preserve the space of " ":
                    node: p.lastChild, // " "
                    direction: DIRECTIONS.LEFT,
                    // The DOM used to be `<p>a  b</p>` so to the left of " b" we
                    // used to see " " which is visible space.
                    cType: CTYPES.SPACE,
                });
                // Now looking to the left of " " we see " " which is now
                // invisible. This means the space we're examining is also still
                // invisible. Since it should be invisible, we should get back a
                // rule that will enforce the invisibility of the space (but no
                // rule would work as well).
                window.chai.expect(rule.spaceVisibility).not.to.be.true;
            });
            it('should restore invisible space to the right (looking left) (nothing after)', () => {
                // We'll be restoring the state of " []" in `<p> </p>`.
                const [p] = insertTestHtml('<p>a </p>');
                splitTextNode(p.firstChild, 1); // "a"" "
                const rule = restoreState({
                    // We look to the left of " " (`a[] `) to see if we need
                    // to preserve the space of " ":
                    node: p.lastChild, // " "
                    direction: DIRECTIONS.LEFT,
                    // The DOM used to be `<p> </p>` so to the left of " " we
                    // used to see `<p>`: the opening tag from the inside.
                    cType: CTYPES.BLOCK_INSIDE,
                });
                // Now looking to the left of " " we see "a", which is content
                // but since it's to the left of our space it has no incidence
                // on its visibility. Either way it should be invisible so we
                // should get back a rule that will enforce the invisibility of
                // the space (but no rule would work as well).
                window.chai.expect(rule.spaceVisibility).not.to.be.true;
            });
            it('should restore invisible space to the right (looking left) (more space after)', () => {
                // We'll be restoring the state of " []   " in `<p>    </p>`.
                const [p] = insertTestHtml('<p>a    </p>');
                splitTextNode(p.firstChild, 2); // "a ""   "
                const rule = restoreState({
                    // We look to the left of "   " (`a []   `) to see if we need
                    // to preserve the space of "   ":
                    node: p.lastChild, // "   "
                    direction: DIRECTIONS.LEFT,
                    // The DOM used to be `<p>    </p>` so to the left of "   "
                    // we used to see `<p>`: the opening tag from the inside.
                    cType: CTYPES.BLOCK_INSIDE,
                });
                // Now looking to the left of "   " we see "a", which is content
                // but since it's to the left of our space it has no incidence
                // on its visibility. Either way it should be invisible so we
                // should get back a rule that will enforce the invisibility of
                // the space (but no rule would work as well).
                window.chai.expect(rule.spaceVisibility).not.to.be.true;
            });
            it('should restore invisible space to the right (looking left) (br after)', () => {
                // We'll be restoring the state of " []<br>" in `<p> []<br></p>`.
                const [p] = insertTestHtml('<p>a <br></p>');
                const rule = restoreState({
                    // We look to the left of `<br>` (`a []<br>`):
                    node: p.lastChild, // `<br>`
                    direction: DIRECTIONS.LEFT,
                    // The DOM used to be `<p> <br></p>` so to the left of
                    // `<br>` we used to see `<p>`: the opening tag from the
                    // inside.
                    cType: CTYPES.BLOCK_INSIDE,
                });
                // Now looking to the left of `<br>` we see "a", which is
                // content but since it's to the left of our space it has no
                // incidence on its visibility. Either way it should be
                // invisible so we should get back a rule that will enforce the
                // invisibility of the space (but no rule would work as well).
                window.chai.expect(rule.spaceVisibility).not.to.be.true;
            });
        });
        describe('enforceWhitespace', () => {
            it('should enforce invisible space to the left', () => {
                // We'll be making the space between "a" and "b" invisible.
                const [p] = insertTestHtml('<p>a b</p>');
                splitTextNode(p.firstChild, 2); // "a ""b"
                // We look to the left while standing at "a []":
                enforceWhitespace(p, 1, DIRECTIONS.LEFT, { spaceVisibility: false });
                window.chai.expect(p.innerHTML).to.eql('ab');
            });
            it('should restore visible space to the left (among consecutive space within content)', () => {
                // We'll be making the first space after "a" visible.
                const [p] = insertTestHtml('<p>a  </p>');
                splitTextNode(p.firstChild, 2); // "a "" "
                // We look to the left while standing at "a []":
                enforceWhitespace(p, 1, DIRECTIONS.LEFT, { spaceVisibility: true });
                window.chai.expect(p.innerHTML).to.eql('a&nbsp; ');
            });
            it('should not enforce already invisible space to the right (followed by consecutive space within content)', () => {
                // We'll be keeping the last (invisible) space after "a" (we
                // could remove it but we don't need to - mostly we should not
                // make it visible).
                const [p] = insertTestHtml('<p>a  </p>');
                splitTextNode(p.firstChild, 2); // "a "" "
                // We look to the left while standing at "a []":
                enforceWhitespace(p, 0, DIRECTIONS.RIGHT, { spaceVisibility: false });
                window.chai.expect(p.innerHTML).to.eql('a  ');
            });
            it('should not enforce already invisible space to the right (nothing after)', () => {
                // We'll be keeping the invisible space after "a" (we could
                // remove it but we don't need to - mostly we should not make it
                // visible).
                const [p] = insertTestHtml('<p>a </p>');
                splitTextNode(p.firstChild, 1); // "a"" "
                // We look to the right while standing at "a[]":
                enforceWhitespace(p, 0, DIRECTIONS.RIGHT, { spaceVisibility: false });
                window.chai.expect(p.innerHTML).to.eql('a ');
            });
            it('should not enforce already invisible space to the left (more space after)', () => {
                // We'll be keeping the invisible space after "a" (we could
                // remove it but we don't need to - mostly we should not make it
                // visible).
                const [p] = insertTestHtml('<p>a    </p>');
                splitTextNode(p.firstChild, 1); // "a""    "
                // We look to the right while standing at "a[]":
                enforceWhitespace(p, 0, DIRECTIONS.RIGHT, { spaceVisibility: false });
                window.chai.expect(p.innerHTML).to.eql('a    ');
            });
            it('should not enforce already invisible space to the left (br after)', () => {
                // We'll be keeping the invisible space after "a" (we could
                // remove it but we don't need to - mostly we should not make it
                // visible).
                const [p] = insertTestHtml('<p>a <br></p>');
                splitTextNode(p.firstChild, 1); // "a"" "
                // We look to the right while standing at "a[]":
                enforceWhitespace(p, 0, DIRECTIONS.RIGHT, { spaceVisibility: false });
                window.chai.expect(p.innerHTML).to.eql('a <br>');
            });
        });
    });
});
