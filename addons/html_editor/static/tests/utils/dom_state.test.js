import { CTYPES } from "@html_editor/utils/content_types";
import { enforceWhitespace, getState, restoreState } from "@html_editor/utils/dom_state";
import { DIRECTIONS } from "@html_editor/utils/position";
import { describe, expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";

describe("getState", () => {
    test("should recognize invisible space to the right", async () => {
        // We'll be looking to the right while standing at `a[] `.
        const { el, editor } = await setupEditor("<p>a </p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 1); // "a"" "
        expect(p.childNodes.length).toBe(2);
        const position = [p, 1]; // `<p>"a"[]" "</p>`
        expect(getState(...position, DIRECTIONS.RIGHT)).toEqual({
            // We look to the right of "a" (`a[] `):
            node: p.firstChild, // "a"
            direction: DIRECTIONS.RIGHT,
            // The browser strips the space away so we ignore it and see
            // `</p>`: the closing tag from the inside.
            cType: CTYPES.BLOCK_INSIDE,
        });
    });

    test("should recognize invisible space to the right (among consecutive space within content)", async () => {
        // We'll be looking to the right while standing at `a [] `. The
        // first space is visible, the rest isn't.
        const { el, editor } = await setupEditor("<p>a  b</p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 2); // "a "" b"
        expect(p.childNodes.length).toBe(2);
        const position = [p, 1]; // `<p>"a "[]" b"</p>`
        expect(getState(...position, DIRECTIONS.RIGHT)).toEqual({
            // We look to the right of "a " (`a []`):
            node: p.firstChild, // "a "
            direction: DIRECTIONS.RIGHT,
            // The browser strips the space away so we ignore it and see
            // "b": visible content.
            cType: CTYPES.CONTENT,
        });
    });

    test("should recognize visible space to the left (followed by consecutive space within content)", async () => {
        // We'll be looking to the left while standing at `[] b`. The
        // first space is visible, the rest isn't.
        const { el, editor } = await setupEditor("<p>a  b</p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 2); // "a "" b"
        expect(p.childNodes.length).toBe(2);
        const position = [p, 1]; // `<p>"a "[]" b"</p>`
        expect(getState(...position, DIRECTIONS.LEFT)).toEqual({
            // We look to the left of " b" (`[] b`):
            node: p.lastChild, // "a"
            direction: DIRECTIONS.LEFT,
            // Left of " b" we see visible space that we should
            // preserve.
            cType: CTYPES.SPACE,
        });
    });

    test("should recognize invisible space to the left (nothing after)", async () => {
        // We'll be looking to the left while standing at ` [] `.
        const { el } = await setupEditor("<p> </p>");
        const p = el.firstChild;
        p.append(document.createTextNode("")); // " """
        expect(getState(p, 1, DIRECTIONS.LEFT)).toEqual({
            // We look to the left of " " (` []`):
            node: p.lastChild, // ""
            direction: DIRECTIONS.LEFT,
            // The browser strips the space away so we ignore it and see
            // `<p>`: the opening tag from the inside.
            cType: CTYPES.BLOCK_INSIDE,
        });
    });

    test("should recognize invisible space to the left (more space after)", async () => {
        // We'll be looking to the left while standing at ` [] `.
        const { el, editor } = await setupEditor("<p>    </p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 1); // " ""   "
        expect(getState(p, 1, DIRECTIONS.LEFT)).toEqual({
            // We look to the left of "   " (` []   `):
            node: p.lastChild, // "   ".
            direction: DIRECTIONS.LEFT,
            // The browser strips the space away so we ignore it and see
            // `<p>`: the opening tag from the inside.
            cType: CTYPES.BLOCK_INSIDE,
        });
    });

    test("should recognize invisible space to the left (br after)", async () => {
        // We'll be looking to the left while standing at ` [] `.
        const { el } = await setupEditor("<p> <br></p>");
        const p = el.firstChild;
        expect(getState(p, 1, DIRECTIONS.LEFT)).toEqual({
            // We look to the left of the br element (` []<br>`):
            node: p.lastChild, // `<br>`.
            direction: DIRECTIONS.LEFT,
            // The browser strips the space away so we ignore it and see
            // `<p>`: the opening tag from the inside.
            cType: CTYPES.BLOCK_INSIDE,
        });
    });
});

describe("restoreState", () => {
    test("should restore invisible space to the left (looking right)", async () => {
        // We'll be restoring the state of "a []" in `<p>a </p>`.
        const { el, editor } = await setupEditor("<p>a b</p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 2); // "a ""b"
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
        expect(rule.spaceVisibility).not.toBe(true);
    });

    test("should restore visible space to the left (looking right) (among consecutive space within content)", async () => {
        // We'll be restoring the state of "a []" in `<p>a  b</p>`.
        // The first space is visible, the rest isn't.
        const { el, editor } = await setupEditor("<p>a  </p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 2); // "a "" "
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
        expect(rule.spaceVisibility).toBe(true);
    });

    test("should restore visible space to the right (looking left) (followed by consecutive space within content)", async () => {
        // We'll be restoring the state of "[] b" in `<p>a  b</p>`.
        // The first space is visible, the rest isn't.
        const { el, editor } = await setupEditor("<p>a  </p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 2); // "a "" "
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
        expect(rule.spaceVisibility).not.toBe(true);
    });

    test("should restore invisible space to the right (looking left) (nothing after)", async () => {
        // We'll be restoring the state of " []" in `<p> </p>`.
        const { el, editor } = await setupEditor("<p>a </p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 1); // "a"" "
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
        expect(rule.spaceVisibility).not.toBe(true);
    });

    test("should restore invisible space to the right (looking left) (more space after)", async () => {
        // We'll be restoring the state of " []   " in `<p>    </p>`.
        const { el, editor } = await setupEditor("<p>a    </p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 2); // "a ""   "
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
        expect(rule.spaceVisibility).not.toBe(true);
    });

    test("should restore invisible space to the right (looking left) (br after)", async () => {
        // We'll be restoring the state of " []<br>" in `<p> []<br></p>`.
        const { el } = await setupEditor("<p>a <br></p>");
        const p = el.firstChild;
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
        expect(rule.spaceVisibility).not.toBe(true);
    });
});

describe("enforceWhitespace", () => {
    test("should enforce invisible space to the left", async () => {
        // We'll be making the space between "a" and "b" invisible.
        const { el, editor } = await setupEditor("<p>a b</p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 2); // "a ""b"
        // We look to the left while standing at "a []":
        enforceWhitespace(p, 1, DIRECTIONS.LEFT, { spaceVisibility: false });
        expect(p.innerHTML).toBe("ab");
    });

    test("should restore visible space to the left (among consecutive space within content)", async () => {
        // We'll be making the first space after "a" visible.
        const { el, editor } = await setupEditor("<p>a  </p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 2); // "a "" "
        // We look to the left while standing at "a []":
        enforceWhitespace(p, 1, DIRECTIONS.LEFT, { spaceVisibility: true });
        expect(p.innerHTML).toBe("a&nbsp; ");
    });

    test("should not enforce already invisible space to the right (followed by consecutive space within content)", async () => {
        // We'll be keeping the last (invisible) space after "a" (we
        // could remove it but we don't need to - mostly we should not
        // make it visible).
        const { el, editor } = await setupEditor("<p>a  </p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 2); // "a "" "
        // We look to the left while standing at "a []":
        enforceWhitespace(p, 0, DIRECTIONS.RIGHT, { spaceVisibility: false });
        expect(p.innerHTML).toBe("a  ");
    });

    test("should not enforce already invisible space to the right (nothing after)", async () => {
        // We'll be keeping the invisible space after "a" (we could
        // remove it but we don't need to - mostly we should not make it
        // visible).
        const { el, editor } = await setupEditor("<p>a </p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 1); // "a"" "
        // We look to the right while standing at "a[]":
        enforceWhitespace(p, 0, DIRECTIONS.RIGHT, { spaceVisibility: false });
        expect(p.innerHTML).toBe("a ");
    });

    test("should not enforce already invisible space to the left (more space after)", async () => {
        // We'll be keeping the invisible space after "a" (we could
        // remove it but we don't need to - mostly we should not make it
        // visible).
        const { el, editor } = await setupEditor("<p>a    </p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 1); // "a""    "
        // We look to the right while standing at "a[]":
        enforceWhitespace(p, 0, DIRECTIONS.RIGHT, { spaceVisibility: false });
        expect(p.innerHTML).toBe("a    ");
    });

    test("should not enforce already invisible space to the left (br after)", async () => {
        // We'll be keeping the invisible space after "a" (we could
        // remove it but we don't need to - mostly we should not make it
        // visible).
        const { el, editor } = await setupEditor("<p>a <br></p>");
        const p = el.firstChild;
        editor.shared.splitTextNode(p.firstChild, 1); // "a"" "
        // We look to the right while standing at "a[]":
        enforceWhitespace(p, 0, DIRECTIONS.RIGHT, { spaceVisibility: false });
        expect(p.innerHTML).toBe("a <br>");
    });
});
