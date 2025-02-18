import { describe, test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { deleteBackward, deleteForward } from "../_helpers/user_actions";
import { unformat } from "../_helpers/format";

describe("backward", () => {
    describe("selection collapsed", () => {
        describe("start empty", () => {
            test("should delete empty p after an unbreakable (backward)", async () => {
                await testEditor({
                    contentBefore: `<div class="oe_unbreakable">a</div><p>[]<br></p>`,
                    stepFunction: deleteBackward,
                    contentAfter: `<div class="oe_unbreakable">a[]</div>`,
                });
            });
            test("should delete empty p/br after an unbreakable (backward)", async () => {
                await testEditor({
                    contentBefore: `<div class="oe_unbreakable">a</div><p>[]<br></p>`,
                    stepFunction: deleteBackward,
                    contentAfter: `<div class="oe_unbreakable">a[]</div>`,
                });
            });
            test("should delete empty unbreakable (backward)", async () => {
                await testEditor({
                    contentBefore: unformat(`
                    <div>
                        <div><p>a</p></div>
                        <div class="oe_unbreakable">[]</div>
                    </div>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                    <div>
                        <div>
                            <p>a[]</p>
                        </div>
                    </div>`),
                });
            });
            test("should not delete an empty unbreakable when there is no elements to delete before (backward)", async () => {
                await testEditor({
                    contentBefore: unformat(`
                        <div>
                            <div class="oe_unbreakable">[]<br></div>
                            <p>a</p>
                        </div>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                        <div>
                            <div class="oe_unbreakable">[]<br></div>
                            <p>a</p>
                        </div>`),
                });
            });
        });

        describe("start text", () => {
            test("should not merge p with an unbreakable (backward)", async () => {
                await testEditor({
                    contentBefore: `<div class="oe_unbreakable">b</div><p>[]a</p>`,
                    stepFunction: deleteBackward,
                    contentAfter: `<div class="oe_unbreakable">b</div><p>[]a</p>`,
                });
            });
            test("should not merge unbreakable before an unbreakable (backward)", async () => {
                await testEditor({
                    contentBefore: unformat(`
                        <div>
                            <div class="oe_unbreakable">a</div>
                            <div class="oe_unbreakable">[]b</div>
                        </div>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                        <div>
                            <div class="oe_unbreakable">a</div>
                            <div class="oe_unbreakable">[]b</div>
                        </div>`),
                });
            });
            test("should not merge unbreakable before a p (backward)", async () => {
                await testEditor({
                    contentBefore: unformat(`
                        <div>
                            <p>a</p>
                            <div class="oe_unbreakable">[]b</div>
                        </div>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                        <div>
                            <p>a</p>
                            <div class="oe_unbreakable">[]b</div>
                        </div>`),
                });
            });
            test("should not merge unbreakable before an empty unbreakable (backward)", async () => {
                await testEditor({
                    contentBefore: unformat(`
                        <div>
                            <div class="oe_unbreakable"><br></div>
                            <div class="oe_unbreakable">[]b</div>
                        </div>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                        <div>
                            <div class="oe_unbreakable"><br></div>
                            <div class="oe_unbreakable">[]b</div>
                        </div>`),
                });
            });
            test("should not merge unbreakable before an empty p (backward)", async () => {
                await testEditor({
                    contentBefore: unformat(`
                        <div>
                            <p><br></p>
                            <div class="oe_unbreakable">[]b</div>
                        </div>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                        <div>
                            <p><br></p>
                            <div class="oe_unbreakable">[]b</div>
                        </div>`),
                });
            });
        });
    });
    describe("selection not collapsed", () => {
        describe("monolevel", () => {
            describe("anchor start", () => {
                test("should remove sandwitched unbreakable (anchor start, focus start) (backward)", async () => {
                    await testEditor({
                        contentBefore: unformat(`
                            <div>
                                <div class="oe_unbreakable">[ab</div>
                                <div class="oe_unbreakable">cd</div>
                                <div class="oe_unbreakable">ef]</div>
                            </div>`),
                        stepFunction: deleteBackward,
                        contentAfter: unformat(`
                            <div>
                                <div class="oe_unbreakable">[]<br></div>
                            </div>`),
                    });
                });
                test("should remove sandwitched unbreakable (anchor start, focus between) (backward)", async () => {
                    await testEditor({
                        contentBefore: unformat(`
                            <div>
                                <div class="oe_unbreakable">[ab</div>
                                <div class="oe_unbreakable">cd</div>
                                <div class="oe_unbreakable">e]f</div>
                            </div>`),
                        stepFunction: deleteBackward,
                        contentAfter: unformat(`
                            <div>
                                <div class="oe_unbreakable">[]f</div>
                            </div>`),
                    });
                });
            });

            describe("anchor between", () => {
                test("should remove sandwitched unbreakable (anchor between, focus between) (backward)", async () => {
                    await testEditor({
                        contentBefore: unformat(`
                            <div>
                                <div class="oe_unbreakable">a[b</div>
                                <div class="oe_unbreakable">cd</div>
                                <div class="oe_unbreakable">e]f</div>
                            </div>`),
                        stepFunction: deleteBackward,
                        contentAfter: unformat(`
                            <div>
                                <div class="oe_unbreakable">a[]</div>
                                <div class="oe_unbreakable">f</div>
                            </div>`),
                    });
                });
                test("should remove sandwitched unbreakable (anchor between, focus end) (backward)", async () => {
                    await testEditor({
                        contentBefore: unformat(`
                            <div>
                                <div class="oe_unbreakable">a[b</div>
                                <div class="oe_unbreakable">cd</div>
                                <div class="oe_unbreakable">ef]</div>
                            </div>`),
                        stepFunction: deleteBackward,
                        contentAfter: unformat(`
                            <div>
                                <div class="oe_unbreakable">a[]</div>
                            </div>`),
                    });
                });
            });
        });

        describe("multilevel", () => {
            describe("anchor start", () => {
                test("should remove sandwitched unbreakable (multilevel, anchor start, focus between) (backward)", async () => {
                    await testEditor({
                        contentBefore: unformat(`
                            <div>
                                <div class="oe_unbreakable">[ab</div>
                                <div class="oe_unbreakable">cd</div>
                                <div class="oe_unbreakable">ef</div>
                            </div>
                            <div>
                                <div class="oe_unbreakable">gh</div>
                                <div class="oe_unbreakable">ij</div>
                                <div class="oe_unbreakable">k]l</div>
                            </div>`),
                        stepFunction: deleteBackward,
                        contentAfter: unformat(`
                            <div>
                                <div class="oe_unbreakable">[]l</div>
                            </div>`),
                    });
                });
            });
            describe("anchor between", () => {
                test("should remove sandwitched unbreakable (multilevel, anchor between, focus between) (backward)", async () => {
                    await testEditor({
                        contentBefore: unformat(`
                            <div>
                                <div class="oe_unbreakable">a[b</div>
                                <div class="oe_unbreakable">cd</div>
                                <div class="oe_unbreakable">ef</div>
                            </div>
                            <div>
                                <div class="oe_unbreakable">gh</div>
                                <div class="oe_unbreakable">ij</div>
                                <div class="oe_unbreakable">k]l</div>
                            </div>`),
                        stepFunction: deleteBackward,
                        contentAfter: unformat(`
                            <div>
                                <div class="oe_unbreakable">a[]</div>
                            </div>
                            <div>
                                <div class="oe_unbreakable">l</div>
                            </div>`),
                    });
                });
                test("should remove sandwitched unbreakable (multilevel, anchor between, focus end) (backward)", async () => {
                    await testEditor({
                        contentBefore: unformat(`
                            <div>
                                <div class="oe_unbreakable">a[b</div>
                                <div class="oe_unbreakable">cd</div>
                                <div class="oe_unbreakable">ef</div>
                            </div>
                            <div>
                                <div class="oe_unbreakable">gh</div>
                                <div class="oe_unbreakable">ij</div>
                                <div class="oe_unbreakable">kl]</div>
                            </div>`),
                        stepFunction: (editor) => deleteBackward(editor),
                        contentAfter: unformat(`
                            <div>
                                <div class="oe_unbreakable">a[]</div>
                            </div>`),
                    });
                });
            });
        });

        test("should delete last character of paragraph but not merge it with unbreakable", async () => {
            await testEditor({
                contentBefore: `<p>ab[c</p><p class="oe_unbreakable">]def</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>ab[]</p><p class="oe_unbreakable">def</p>`,
            });
        });

        test("should delete last character of paragraph and fully selected empty unbreakable", async () => {
            await testEditor({
                contentBefore: `<p>ab[c</p><p class="oe_unbreakable">]<br></p><p>def</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>ab[]</p><p>def</p>`,
            });
        });

        test("should delete first character of unbreakable, ignoring selected paragraph break (backward)", async () => {
            await testEditor({
                contentBefore: `<p>abc[</p><p class="oe_unbreakable">d]ef</p>`,
                stepFunction: deleteBackward,
                contentAfter: `<p>abc[]</p><p class="oe_unbreakable">ef</p>`,
            });
        });
    });
});
describe("forward", () => {
    describe("selection collapsed", () => {
        describe("start empty", () => {
            test("should delete empty p just before an unbreakable (forward)", async () => {
                await testEditor({
                    contentBefore: `<p>[]</p><div class="oe_unbreakable">a</div>`,
                    stepFunction: deleteForward,
                    contentAfter: `<div class="oe_unbreakable">[]a</div>`,
                });
            });
            test("should delete empty p/br just before an unbreakable (forward)", async () => {
                await testEditor({
                    contentBefore: `<p><br>[]</p><div class="oe_unbreakable">a</div>`,
                    stepFunction: deleteForward,
                    contentAfter: `<div class="oe_unbreakable">[]a</div>`,
                });
            });
            test("should delete empty unbreakables (forward)", async () => {
                await testEditor({
                    contentBefore: unformat(`
                    <div>
                        <div>[]</div>
                        <div><p>a</p></div>
                    </div>`),
                    stepFunction: deleteForward,
                    contentAfter: unformat(`
                    <div>
                        <div><p>[]a</p></div>
                    </div>`),
                });
            });
            test("should not delete an empty unbreakable when there is no elements to delete after (forward)", async () => {
                await testEditor({
                    contentBefore: unformat(`
                        <div>
                            <p>a</p>
                            <div class="oe_unbreakable">[]<br></div>
                        </div>`),
                    stepFunction: deleteForward,
                    contentAfter: unformat(`
                        <div>
                            <p>a</p>
                            <div class="oe_unbreakable">[]<br></div>
                        </div>`),
                });
            });
        });

        describe("start text", () => {
            test("should not merge p with an unbreakable (forward)", async () => {
                await testEditor({
                    contentBefore: `<p>a[]</p><div class="oe_unbreakable">b</div>`,
                    stepFunction: deleteForward,
                    contentAfter: `<p>a[]</p><div class="oe_unbreakable">b</div>`,
                });
            });
            test("should not remove unbreakable after an unbreakable (forward)", async () => {
                await testEditor({
                    contentBefore: unformat(`
                        <div>
                            <div class="oe_unbreakable">b[]</div>
                            <div class="oe_unbreakable">a</div>
                        </div>`),
                    stepFunction: deleteForward,
                    contentAfter: unformat(`
                        <div>
                            <div class="oe_unbreakable">b[]</div>
                            <div class="oe_unbreakable">a</div>
                        </div>`),
                });
            });
            test("should not merge unbreakable after a p (forward)", async () => {
                await testEditor({
                    contentBefore: unformat(`
                        <div>
                            <div class="oe_unbreakable">b[]</div>
                            <p>a</p>
                        </div>`),
                    stepFunction: deleteForward,
                    contentAfter: unformat(`
                        <div>
                            <div class="oe_unbreakable">b[]</div>
                            <p>a</p>
                        </div>`),
                });
            });
            test("should not merge unbreakable after an empty unbreakable (forward)", async () => {
                await testEditor({
                    contentBefore: unformat(`
                        <div>
                            <div class="oe_unbreakable">b[]</div>
                            <div class="oe_unbreakable"><br></div>
                        </div>`),
                    stepFunction: deleteForward,
                    contentAfter: unformat(`
                        <div>
                            <div class="oe_unbreakable">b[]</div>
                            <div class="oe_unbreakable"><br></div>
                        </div>`),
                });
            });
            test("should not merge unbreakable after an empty p (forward)", async () => {
                await testEditor({
                    contentBefore: unformat(`
                        <div>
                            <div class="oe_unbreakable">b[]</div>
                            <p><br></p>
                        </div>`),
                    stepFunction: deleteForward,
                    contentAfter: unformat(`
                        <div>
                            <div class="oe_unbreakable">b[]</div>
                            <p><br></p>
                        </div>`),
                });
            });
        });
    });
    // Only few tests are made with the selection not collapsed it should use the
    // same logic as for the backward (deleteRange).
    describe("selection not collapsed", () => {
        test("should not break unbreakables (delete forward) (1)", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <div>
                            <div class="oe_unbreakable">a[bc</div>
                            <div class="oe_unbreakable">de]f</div>
                        </div>`),
                stepFunction: deleteForward,
                contentAfter: unformat(`
                        <div>
                            <div class="oe_unbreakable">a[]</div>
                            <div class="oe_unbreakable">f</div>
                        </div>`),
            });
        });

        test("should not break unbreakables (delete forward) (2)", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <p class="oe_unbreakable">a[b</p>
                        <p class="oe_unbreakable">c]d</p>`),
                stepFunction: deleteForward,
                contentAfter: unformat(`
                        <p class="oe_unbreakable">a[]</p>
                        <p class="oe_unbreakable">d</p>`), // JW without oe_breakable classes of course
            });
        });

        test("should delete first character of unbreakable, ignoring selected paragraph break (forward)", async () => {
            await testEditor({
                contentBefore: '<p>abc[</p><p class="oe_unbreakable">d]ef</p>',
                stepFunction: deleteForward,
                contentAfter: '<p>abc[]</p><p class="oe_unbreakable">ef</p>',
            });
        });
    });
});

describe("list", () => {
    describe("selection collapsed", () => {
        test("should not outdent while nested within a list item if the list is unbreakable", async () => {
            // Only one LI.
            await testEditor({
                contentBefore: '<p>abc</p><ol class="oe_unbreakable"><li>[]def</li></ol>',
                stepFunction: deleteBackward,
                contentAfter: '<p>abc</p><ol class="oe_unbreakable"><li>[]def</li></ol>',
            });
            // First LI.
            await testEditor({
                contentBefore:
                    '<ol class="oe_unbreakable"><li><div><div>[]abc</div></div></li><li>def</li></ol>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<ol class="oe_unbreakable"><li><div><div>[]abc</div></div></li><li>def</li></ol>',
            });
            // In the middle.
            await testEditor({
                contentBefore:
                    '<ol class="oe_unbreakable"><li><div>abc</div></li><li><div><div>[]def</div></div></li><li>ghi</li></ol>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<ol class="oe_unbreakable"><li><div>abc</div></li><li><div><div>[]def</div></div></li><li>ghi</li></ol>',
            });
            // Last LI.
            await testEditor({
                contentBefore:
                    '<ol class="oe_unbreakable"><li>abc</li><li><div><div>[]def</div></div></li></ol>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<ol class="oe_unbreakable"><li>abc</li><li><div><div>[]def</div></div></li></ol>',
            });
            // With a div before the list:
            await testEditor({
                contentBefore:
                    '<div>abc</div><ol class="oe_unbreakable"><li>def</li><li><div><div>[]ghi</div></div></li><li>jkl</li></ol>',
                stepFunction: deleteBackward,
                contentAfter:
                    '<div>abc</div><ol class="oe_unbreakable"><li>def</li><li><div><div>[]ghi</div></div></li><li>jkl</li></ol>',
            });
        });
        test("shoud not outdent list item in unsplittable list, but merge with previous LI", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <ol class="oe_unbreakable">
                        <li>abc</li>
                        <li>[]def</li>
                    </ol>`),
                stepFunction: deleteBackward,
                contentAfter: unformat(`
                    <ol class="oe_unbreakable">
                        <li>abc[]def</li>
                    </ol>`),
            });
        });
        test("shoud not outdent list item in unsplittable list, nor merge it with previous block", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <p>abc</p>
                    <ol class="oe_unbreakable">
                        <li>[]abc</li>
                        <li>def</li>
                    </ol>`),
                stepFunction: deleteBackward,
                contentAfter: unformat(`
                    <p>abc</p>
                    <ol class="oe_unbreakable">
                        <li>[]abc</li>
                        <li>def</li>
                    </ol>`),
            });
        });
        test("shoud not outdent list item nested in unsplittable list", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <p>abc</p>
                    <ol class="oe_unbreakable">
                        <li class="oe-nested">
                            <ol>
                                <li>[]abc</li>
                                <li>def</li>
                            </ol>
                        </li>
                    </ol>`),
                stepFunction: deleteBackward,
                contentAfter: unformat(`
                    <p>abc</p>
                    <ol class="oe_unbreakable">
                        <li class="oe-nested">
                            <ol>
                                <li>[]abc</li>
                                <li>def</li>
                            </ol>
                        </li>
                    </ol>`),
            });
        });
    });
    describe("selection not collapsed", () => {
        test("shoud not merge list item in the previous unbreakable sibling (1)", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <p class="oe_unbreakable">a[bc</p>
                        <ol>
                            <li>d]ef</li>
                            <li>ghi</li>
                        </ol>`),
                stepFunction: deleteBackward,
                contentAfter: unformat(`
                        <p class="oe_unbreakable">a[]</p>
                        <ol>
                            <li>ef</li>
                            <li>ghi</li>
                        </ol>`),
            });
        });

        test("shoud not merge list item in the previous unbreakable sibling (2)", async () => {
            await testEditor({
                contentBefore: unformat(`
                        <div class="oe_unbreakable">
                            <p>a[bc</p>
                        </div>
                        <ol>
                            <li>d]ef</li>
                            <li>ghi</li>
                        </ol>`),
                stepFunction: deleteBackward,
                contentAfter: unformat(`
                        <div class="oe_unbreakable">
                            <p>a[]</p>
                        </div>
                        <ol>
                            <li>ef</li>
                            <li>ghi</li>
                        </ol>`),
            });
        });
    });
});
