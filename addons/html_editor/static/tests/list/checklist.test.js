import { test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { clickCheckbox, pasteHtml } from "../_helpers/user_actions";
import { click } from "@odoo/hoot-dom";

test("should do nothing if do not click on the checkbox", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ul class="o_checklist">
                <li>1</li>
            </ul>`),
        stepFunction: async (editor) => {
            const li = editor.editable.querySelector("li");
            const liRect = li.getBoundingClientRect();
            await click(li, { position: { clientX: liRect.left + 10, clientY: liRect.top + 10 } });
        },
        contentAfter: unformat(`
            <ul class="o_checklist">
                <li>1</li>
            </ul>`),
    });
});

test("should check a simple item", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ul class="o_checklist">
                <li>1</li>
            </ul>`),
        stepFunction: async (editor) => {
            const li = editor.editable.querySelector("li");
            await clickCheckbox(li);
        },
        contentAfter: unformat(`
            <ul class="o_checklist">
                <li class="o_checked">[]1</li>
            </ul>`),
    });
});

test("should uncheck a simple item", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ul class="o_checklist">
                <li class="o_checked">1</li>
            </ul>`),
        stepFunction: async (editor) => {
            const li = editor.editable.querySelector("li");
            await clickCheckbox(li);
        },
        contentAfter: unformat(`
                <ul class="o_checklist">
                    <li>[]1</li>
                </ul>`),
    });
});

test("should check an empty item", async () => {
    await testEditor({
        contentBefore: unformat(`
                <ul class="o_checklist">
                    <li><br></li>
                </ul>`),
        stepFunction: async (editor) => {
            const li = editor.editable.querySelector("li");
            await clickCheckbox(li);
        },
        contentAfter: unformat(`
            <ul class="o_checklist">
                <li class="o_checked">[]<br></li>
            </ul>`),
    });
});

test("should uncheck an empty item", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ul class="o_checklist">
                <li><br></li>
            </ul>`),
        stepFunction: async (editor) => {
            const li = editor.editable.querySelector("li");
            await clickCheckbox(li);
        },
        contentAfter: unformat(`
            <ul class="o_checklist">
                <li class="o_checked">[]<br></li>
            </ul>`),
    });
});

test("should check a nested item and the previous checklist item used as title", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ul class="o_checklist">
                <li>2</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li class="o_checked">2.1</li>
                        <li>2.2</li>
                    </ul>
                </li>
            </ul>`),
        stepFunction: async (editor) => {
            const lis = editor.editable.querySelectorAll(
                '.o_checklist > li:not([class^="oe-nested"])'
            );
            const li = lis[2];
            await clickCheckbox(li);
        },
        contentAfter: unformat(`
            <ul class="o_checklist">
                <li>2</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li class="o_checked">2.1</li>
                        <li class="o_checked">[]2.2</li>
                    </ul>
                </li>
            </ul>`),
    });
});

test("should uncheck a nested item and the previous checklist item used as title", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ul class="o_checklist">
                <li class="o_checked">2</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li class="o_checked">2.1</li>
                        <li class="o_checked">2.2</li>
                    </ul>
                </li>
            </ul>`),
        stepFunction: async (editor) => {
            const lis = editor.editable.querySelectorAll(
                '.o_checklist > li:not([class^="oe-nested"])'
            );
            const li = lis[2];
            await clickCheckbox(li);
        },
        contentAfter: unformat(`
            <ul class="o_checklist">
                <li class="o_checked">2</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li class="o_checked">2.1</li>
                        <li>[]2.2</li>
                    </ul>
                </li>
            </ul>`),
    });
});

test("should check a nested item and the wrapper wrapper title", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ul class="o_checklist">
                <li>3</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li>3.1</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.2.1</li>
                                <li>3.2.2</li>
                            </ul>
                        </li>
                    </ul>
                </li>
            </ul>`),
        stepFunction: async (editor) => {
            const lis = editor.editable.querySelectorAll(
                '.o_checklist > li:not([class^="oe-nested"])'
            );
            const li = lis[3];
            await clickCheckbox(li);
        },
        contentAfter: unformat(`
            <ul class="o_checklist">
                <li>3</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li>3.1</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.2.1</li>
                                <li class="o_checked">[]3.2.2</li>
                            </ul>
                        </li>
                    </ul>
                </li>
            </ul>`),
    });
});

test("should uncheck a nested item and the wrapper wrapper title", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ul class="o_checklist">
                <li class="o_checked">3</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li class="o_checked">3.1</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.1.1</li>
                                <li class="o_checked">3.1.2</li>
                            </ul>
                        </li>
                    </ul>
                </li>
            </ul>`),
        stepFunction: async (editor) => {
            const lis = editor.editable.querySelectorAll(
                '.o_checklist > li:not([class^="oe-nested"])'
            );
            const li = lis[3];
            await clickCheckbox(li);
        },
        contentAfter: unformat(`
            <ul class="o_checklist">
                <li class="o_checked">3</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li class="o_checked">3.1</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.1.1</li>
                                <li>[]3.1.2</li>
                            </ul>
                        </li>
                    </ul>
                </li>
            </ul>`),
    });
});

// @todo @phoenix: this test's contentAfter does not match its description.
test("should check all nested checklist item", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ul class="o_checklist">
                <li>3</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li>3.1</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.1.1</li>
                                <li>3.1.2</li>
                            </ul>
                        </li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.2.1</li>
                                <li>3.2.2</li>
                            </ul>
                        </li>
                        <li>3.3</li>
                    </ul>
                </li>
            </ul>`),
        stepFunction: async (editor) => {
            const lis = editor.editable.querySelectorAll(
                '.o_checklist > li:not([class^="oe-nested"])'
            );
            const li = lis[0];
            await clickCheckbox(li);
        },
        contentAfter: unformat(`
            <ul class="o_checklist">
                <li class="o_checked">[]3</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li>3.1</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.1.1</li>
                                <li>3.1.2</li>
                                <li class="o_checked">3.2.1</li>
                                <li>3.2.2</li>
                            </ul>
                        </li>
                        <li>3.3</li>
                    </ul>
                </li>
            </ul>`),
    });
});

// @todo @phoenix: this test's contentAfter does not match its description.
test("should uncheck all nested checklist item", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ul class="o_checklist">
                <li class="o_checked">3</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li class="o_checked">3.1</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.1.1</li>
                                <li class="o_checked">3.1.2</li>
                            </ul>
                        </li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.2.1</li>
                                <li class="o_checked">3.2.2</li>
                            </ul>
                        </li>
                        <li class="o_checked">3.3</li>
                    </ul>
                </li>
            </ul>`),
        stepFunction: async (editor) => {
            const lis = editor.editable.querySelectorAll(
                '.o_checklist > li:not([class^="oe-nested"])'
            );
            const li = lis[0];
            await clickCheckbox(li);
        },
        contentAfter: unformat(`
            <ul class="o_checklist">
                <li>[]3</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li class="o_checked">3.1</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.1.1</li>
                                <li class="o_checked">3.1.2</li>
                                <li class="o_checked">3.2.1</li>
                                <li class="o_checked">3.2.2</li>
                            </ul>
                        </li>
                        <li class="o_checked">3.3</li>
                    </ul>
                </li>
            </ul>`),
    });
});

test("should check all nested checklist item and update wrapper title", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ul class="o_checklist">
                <li>3</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li>3.1</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.2.1</li>
                                <li>3.2.2</li>
                            </ul>
                        </li>
                    </ul>
                </li>
            </ul>`),
        stepFunction: async (editor) => {
            const lis = editor.editable.querySelectorAll(
                '.o_checklist > li:not([class^="oe-nested"])'
            );
            const li = lis[1];
            await clickCheckbox(li);
        },
        contentAfter: unformat(`
            <ul class="o_checklist">
                <li>3</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li class="o_checked">[]3.1</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.2.1</li>
                                <li>3.2.2</li>
                            </ul>
                        </li>
                    </ul>
                </li>
            </ul>`),
    });
});

test("should uncheck all nested checklist items and update wrapper title", async () => {
    await testEditor({
        contentBefore: unformat(`
            <ul class="o_checklist">
                <li class="o_checked">3</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li class="o_checked">3.1</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.2.1</li>
                                <li class="o_checked">3.2.2</li>
                            </ul>
                        </li>
                    </ul>
                </li>
            </ul>`),
        stepFunction: async (editor) => {
            const lis = editor.editable.querySelectorAll(
                '.o_checklist > li:not([class^="oe-nested"])'
            );
            const li = lis[1];
            await clickCheckbox(li);
        },
        contentAfter: unformat(`
            <ul class="o_checklist">
                <li class="o_checked">3</li>
                <li class="oe-nested">
                    <ul class="o_checklist">
                        <li>[]3.1</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.2.1</li>
                                <li class="o_checked">3.2.2</li>
                            </ul>
                        </li>
                    </ul>
                </li>
            </ul>`),
    });
});

test("should preserve list type on paste", async () => {
    await testEditor({
        contentBefore: unformat(`<div></div>`),
        stepFunction: async (editor) => {
            pasteHtml(
                editor,
                `<ul><li>a</li></ul><ul class="o_checklist"><li>b</li><li>c</li><li>d</li></ul>`
            );
        },
        contentAfter: unformat(
            `<ul><li>a</li></ul><ul class="o_checklist"><li>b</li><li>c</li><li>d[]</li></ul><div><br></div>`
        ),
    });
});
