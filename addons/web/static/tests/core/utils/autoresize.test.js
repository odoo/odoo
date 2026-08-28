import { expect, test } from "@odoo/hoot";
import { queryRect, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, signal, useProps, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { useAutoresize } from "@web/core/utils/autoresize";

test(`resizable input`, async () => {
    class ResizableInput extends Component {
        static template = xml`<input class="resizable-input" t-ref="this.inputRef"/>`;
        props = useProps();
        inputRef = signal.ref();

        setup() {
            useAutoresize(this.inputRef);
        }
    }
    await mountWithCleanup(ResizableInput);
    const initialWidth = queryRect(`.resizable-input`).width;

    await contains(`.resizable-input`).edit("new value");
    expect(`.resizable-input`).not.toHaveRect({ width: initialWidth });
});

test(`resizable input sizes to its placeholder when empty`, async () => {
    class ResizableInput extends Component {
        static template = xml`<input class="resizable-input" placeholder="Hi" t-ref="this.inputRef"/>`;
        props = useProps();
        inputRef = signal.ref();

        setup() {
            useAutoresize(this.inputRef);
        }
    }
    await mountWithCleanup(ResizableInput);
    const placeholderWidth = queryRect(`.resizable-input`).width;

    await contains(`.resizable-input`).edit("Hi");
    const typedWidth = queryRect(`.resizable-input`).width;
    // "Hi" placeholder vs "Hi" text should size about the same.
    expect(placeholderWidth).toBeWithin(typedWidth - 5, typedWidth + 5);
});

test(`resizable textarea`, async () => {
    class ResizableTextArea extends Component {
        static template = xml`<textarea class="resizable-textarea" t-ref="this.textareaRef"/>`;
        props = useProps();
        textareaRef = signal.ref();

        setup() {
            useAutoresize(this.textareaRef);
        }
    }
    await mountWithCleanup(ResizableTextArea);
    const initialHeight = queryRect(`.resizable-textarea`).height;

    await contains(`.resizable-textarea`).edit("new value\n".repeat(5));
    expect(`.resizable-textarea`).not.toHaveRect({ height: initialHeight });
});

test(`resizable textarea with minimum height`, async () => {
    class ResizableTextArea extends Component {
        static template = xml`<textarea class="resizable-textarea" t-ref="this.textareaRef"/>`;
        props = useProps();
        textareaRef = signal.ref();

        setup() {
            useAutoresize(this.textareaRef, { minimumHeight: 100 });
        }
    }
    await mountWithCleanup(ResizableTextArea);
    const initialHeight = queryRect(`.resizable-textarea`).height;
    expect(initialHeight).toBe(100);

    await contains(`.resizable-textarea`).edit("new value\n".repeat(5));
    expect(`.resizable-textarea`).not.toHaveRect({ height: initialHeight });
});

test(`call onResize callback`, async () => {
    class ResizableInput extends Component {
        static template = xml`<input class="resizable-input" t-ref="this.inputRef"/>`;
        props = useProps();
        inputRef = signal.ref();

        setup() {
            useAutoresize(this.inputRef, {
                randomParam: true,
                onResize: (el, options) => {
                    expect.step("onResize");
                    expect(el).toBe(this.inputRef());
                    expect(options).toInclude("randomParam");
                },
            });
        }
    }
    await mountWithCleanup(ResizableInput);
    expect.verifySteps(["onResize"]);

    await contains(`.resizable-input`).edit("new value", { instantly: true });
    expect.verifySteps(["onResize"]);
});

test(`call onResize callback after resizing text area`, async () => {
    class ResizableTextArea extends Component {
        static template = xml`<textarea class="resizable-textarea" t-ref="this.textareaRef"/>`;
        props = useProps();
        textareaRef = signal.ref();

        setup() {
            useAutoresize(this.textareaRef, {
                onResize(el, options) {
                    expect.step("onResizeTextArea");
                },
            });
        }
    }
    await mountWithCleanup(ResizableTextArea);
    expect.verifySteps(["onResizeTextArea"]);

    const target = queryOne(".resizable-textarea");
    target.style.width = `500px`;
    await animationFrame();
    expect.verifySteps(["onResizeTextArea"]);
});
