import { expandToolbar } from "@html_editor/../tests/_helpers/toolbar";
import { describe, expect, test, waitFor } from "@odoo/hoot";
import { queryFirst, queryOne } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { setSelection, thirdClick } from "@html_editor/../tests/_helpers/selection";
import { advanceTime } from "@odoo/hoot-mock";

defineWebsiteModels();

const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";

const testImg = `<img data-attachment-id="1" data-original-id="1" data-mimetype="image/png" src='/base/static/img/logo_white.png'>`;

const styleContent = `
.o_animate {
    animation-duration: 1s;
    --wanim-intensity: 50;
}
`;

test("visibility of animation animation=none", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    expect(".options-container [data-label='Effect']").not.toBeVisible();
    expect(".options-container [data-label='Direction']").not.toHaveCount();
    expect(".options-container [data-label='Trigger']").not.toBeVisible();
    expect(".options-container [data-label='Intensity']").not.toHaveCount();
    expect(".options-container [data-label='Start After']").not.toHaveCount();
    expect(".options-container [data-label='Duration']").not.toHaveCount();
});
describe("onAppearance", () => {
    test("visibility of animation animation=onAppearance", async () => {
        const { waitSidebarUpdated } = await setupWebsiteBuilder(
            `
                <div class="test-options-target">
                    ${testImg}
                </div>
            `,
            { styleContent }
        );
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='onAppearance']").click();
        await waitSidebarUpdated();
        expect(".options-container [data-label='Animation'] .o-dropdown").toHaveText(
            "On Appearance"
        );

        expect(".options-container [data-label='Effect'] .o-dropdown").toHaveText("Fade");
        expect(".options-container [data-label='Direction'] .o-dropdown").toHaveText("In place");
        expect(".options-container [data-label='Trigger'] .o-dropdown").toHaveText(
            "First Time Only"
        );
        expect(".options-container [data-label='Intensity']").not.toHaveCount();
        expect(".options-container [data-label='Scroll Zone']").not.toHaveCount();
        expect(".options-container [data-label='Start After'] input").toHaveValue("0");
        expect(".options-container [data-label='Duration'] input").toHaveValue("1");
    });
    test("visibility of animation animation=onAppearance effect=slide", async () => {
        const { waitSidebarUpdated } = await setupWebsiteBuilder(
            `
                <div class="test-options-target">
                    ${testImg}
                </div>
            `,
            { styleContent }
        );
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='onAppearance']").click();

        await contains(".options-container [data-label='Effect'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='o_anim_slide_in']").click();
        await waitSidebarUpdated();
        expect(".options-container [data-label='Effect'] .o-dropdown").toHaveText("Slide");

        expect(".options-container [data-label='Direction'] .o-dropdown").toHaveText("From right");
        expect(".options-container [data-label='Trigger'] .o-dropdown").toHaveText(
            "First Time Only"
        );
        expect(".options-container [data-label='Intensity'] input").toHaveValue(50);
        expect(".options-container [data-label='Scroll Zone']").not.toHaveCount();
        expect(".options-container [data-label='Start After'] input").toHaveValue("0");
        expect(".options-container [data-label='Duration'] input").toHaveValue("1");
    });
    test("visibility of animation animation=onAppearance effect=bounce", async () => {
        const { waitSidebarUpdated } = await setupWebsiteBuilder(
            `
                <div class="test-options-target">
                    ${testImg}
                </div>
            `,
            { styleContent }
        );
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='onAppearance']").click();

        await contains(".options-container [data-label='Effect'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='o_anim_bounce_in']").click();
        await waitSidebarUpdated();
        expect(".options-container [data-label='Effect'] .o-dropdown").toHaveText("Bounce");

        expect(".options-container [data-label='Direction'] .o-dropdown").toHaveText("In place");
        expect(".options-container [data-label='Trigger'] .o-dropdown").toHaveText(
            "First Time Only"
        );
        expect(".options-container [data-label='Intensity'] input").toHaveValue(50);
        expect(".options-container [data-label='Scroll Zone']").not.toHaveCount();
        expect(".options-container [data-label='Start After'] input").toHaveValue("0");
        expect(".options-container [data-label='Duration'] input").toHaveValue("1");
    });
    test("visibility of animation animation=onAppearance effect=flash", async () => {
        const { waitSidebarUpdated } = await setupWebsiteBuilder(
            `
                <div class="test-options-target">
                    ${testImg}
                </div>
            `,
            { styleContent }
        );
        await contains(":iframe .test-options-target img").click();
        await waitSidebarUpdated();

        await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='onAppearance']").click();

        await contains(".options-container [data-label='Effect'] .dropdown-toggle").click();
        await contains(".o-dropdown--menu [data-action-value='o_anim_flash']").click();
        await waitSidebarUpdated();
        expect(".options-container [data-label='Effect'] .o-dropdown").toHaveText("Flash");

        expect(".options-container [data-label='Direction']").not.toHaveCount();
        expect(".options-container [data-label='Trigger'] .o-dropdown").toHaveText(
            "First Time Only"
        );
        expect(".options-container [data-label='Intensity'] input").toHaveValue(50);
        expect(".options-container [data-label='Scroll Zone']").not.toHaveCount();
        expect(".options-container [data-label='Start After'] input").toHaveValue("0");
        expect(".options-container [data-label='Duration'] input").toHaveValue("1");
    });
});
test("visibility of animation animation=onScroll", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='onScroll']").click();
    await waitSidebarUpdated();
    expect(".options-container [data-label='Animation'] .o-dropdown").toHaveText("On Scroll");

    expect(".options-container [data-label='Effect'] .o-dropdown").toHaveText("Fade");
    expect(".options-container [data-label='Direction'] .o-dropdown").toHaveText("In place");

    expect(".options-container [data-label='Trigger']").not.toBeVisible();
    expect(".options-container [data-label='Intensity']").not.toHaveCount();
    expect(".options-container [data-label='Start After']").not.toHaveCount();
    expect(".options-container [data-label='Duration']").not.toHaveCount();

    expect(".options-container [data-label='Scroll Zone']").toBeVisible();
});
test("animation=onScroll should not be visible when the animation is limited", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(
        `
                <div class="test-options-target">
                    ${testImg}
                </div>
            `,
        { styleContent }
    );
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='onAppearance']").click();

    await contains(".options-container [data-label='Effect'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='o_anim_flash']").click();
    await waitSidebarUpdated();
    expect(".options-container [data-label='Effect'] .o-dropdown").toHaveText("Flash");

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    expect(".o-dropdown--menu [data-action-value='onScroll']").not.toHaveCount();
});
test("visibility of animation animation=onHover", async () => {
    function expectOnHoverOptions(options) {
        const labels = [
            "Effect",
            "Direction",
            "Trigger",
            "Intensity",
            "Scroll Zone",
            "Start After",
            "Duration",
            "Color",
            "Overlay",
            "Stroke Width",
        ];
        expect(new Set(labels).isSupersetOf(new Set(Object.keys(options)))).toBe(true, {
            message: `keys not in labels: ${[
                ...new Set(Object.keys(options)).difference(new Set(labels)),
            ].join()}`,
        });
        for (const label of labels) {
            const labelSelector = `.options-container [data-label='${label}']:visible`;
            if (typeof options[label] === "string") {
                expect(labelSelector + " button").toHaveText(options[label]);
            } else {
                expect(labelSelector).toHaveCount(options[label] ?? 0);
            }
        }
    }

    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    // NOTE: we use waitSidebarUpdated because setting the hover effect may
    // take some time (and setting "On Hover" sets a default)

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='onHover']").click();
    await waitSidebarUpdated();
    expect(".options-container [data-label='Animation'] .o-dropdown").toHaveText("On Hover");
    expectOnHoverOptions({ Effect: "Overlay", Color: 1 });

    await contains(".options-container [data-label='Effect'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='image_zoom_in']").click();
    await waitSidebarUpdated();
    expectOnHoverOptions({ Effect: "Zoom In", Intensity: 1, Overlay: 1 });

    await contains(".options-container [data-label='Effect'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='image_zoom_out']").click();
    await waitSidebarUpdated();
    expectOnHoverOptions({ Effect: "Zoom Out", Intensity: 1, Overlay: 1 });

    await contains(".options-container [data-label='Effect'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='dolly_zoom']").click();
    await waitSidebarUpdated();
    expectOnHoverOptions({ Effect: "Dolly Zoom", Intensity: 1, Overlay: 1 });

    await contains(".options-container [data-label='Effect'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='outline']").click();
    await waitSidebarUpdated();
    expectOnHoverOptions({ Effect: "Outline", Color: 1, "Stroke Width": 1 });

    await contains(".options-container [data-label='Effect'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='image_mirror_blur']").click();
    await waitSidebarUpdated();
    expectOnHoverOptions({ Effect: "Mirror Blur", Intensity: 1 });
});
test("animation=onHover should not be visible when the image is a device shape", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            <img data-shape="html_builder/devices/iphone_front_portrait" src='${base64Img}'>
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    expect(".o-dropdown--menu [data-action-value='onHover']").not.toHaveCount();
});
test("animation=onHover should not be visible when the image has a wrong mimetype", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            <img data-attachment-id="1" data-original-id="1" data-mimetype="foo/bar" src='${base64Img}'>
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    expect(".o-dropdown--menu [data-action-value='onHover']").not.toHaveCount();
});
test("animation=onHover should not be visible when the image has a cors protected image", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            <img data-attachment-id="1" data-original-id="1" src='/web/image/0-redirect/foo.jpg'>
        </div>
    `);
    onRpc(
        "/*",
        (req) => {
            const route = new URL(req.url).pathname;
            switch (route) {
                case "/html_editor/get_image_info":
                    return {
                        error: null,
                        result: {
                            attachment: { id: 1 },
                            original: {
                                id: 1,
                                image_src:
                                    "/website/static/src/img/snippets_demo/s_text_image.webp",
                                mimetype: "image/webp",
                            },
                        },
                    };
                case "/website/static/src/img/snippets_demo/s_text_image.webp":
                    return;
                default:
                    expect.step(route);
                    throw new Error("simulated cors error");
            }
        },
        { pure: true }
    );
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    expect.verifySteps(["/web/image/0-redirect/foo.jpg"]);
    expect(".o-dropdown--menu [data-action-value='onHover']").not.toHaveCount();
});

test("image should not be lazy onAppearance", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    expect(":iframe .test-options-target img").toHaveProperty("loading", "auto");

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='onAppearance']").click();
    expect(":iframe .test-options-target img").toHaveProperty("loading", "eager");

    await contains(".options-container [data-label='Animation'] .dropdown-toggle").click();
    await contains(".o-dropdown--menu [data-action-value='']").click();
    expect(":iframe .test-options-target img").toHaveProperty("loading", "auto");
});

test("should not show the animation options if the image has a parent [data-oe-type='image']", async () => {
    const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    expect(".options-container [data-label='Animation'] .dropdown-toggle").toBeVisible();

    const optionTarget = queryFirst(":iframe .test-options-target");
    optionTarget.setAttribute("data-oe-type", "image");
    editor.shared.history.addStep();
    await waitSidebarUpdated();
    expect(".options-container [data-label='Animation'] .dropdown-toggle").not.toHaveCount();
});

test("should not show the animation options if the image has is [data-oe-xpath]", async () => {
    const { getEditor, waitSidebarUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    const editor = getEditor();
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();
    expect(".options-container [data-label='Animation'] .dropdown-toggle").toBeVisible();
    const optionTarget = queryFirst(":iframe .test-options-target img");
    optionTarget.setAttribute("data-oe-xpath", "/foo/bar");
    editor.shared.history.addStep();

    await waitSidebarUpdated();
    expect(".options-container [data-label='Animation'] .dropdown-toggle").not.toHaveCount();
});

test("o_animate should be normalized with loading=eager", async () => {
    await setupWebsiteBuilder(`
        <div class="test-options-target">
            <img class="o_animate" src='${base64Img}'>
        </div>
    `);
    // Should be normalized
    expect(":iframe .test-options-target img").toHaveProperty("loading", "eager");
});

describe("animate text in toolbar", () => {
    test("create a animated span with the selected text", async () => {
        const websiteBuilder = await setupWebsiteBuilder(`<p class="test">abcd</p>`);
        const editable = websiteBuilder.getEditableContent();
        const editor = websiteBuilder.getEditor();
        const selection = editable.ownerDocument.getSelection();

        // Move the selection to open the toolbar
        let textNode = editable.querySelector(".test").childNodes[0];
        selection.setBaseAndExtent(textNode, 1, textNode, 3);

        // click on animate and it create a span with the animation
        await expandToolbar();
        expect("button[title='Animate Text']").not.toHaveClass("active");
        await contains("button[title='Animate Text']").click();
        expect(":iframe span").toHaveText("bc");
        expect(":iframe span:contains('bc')").toHaveClass("o_animate");

        // Move the selection to close the animate popover and the span is still there
        textNode = editable.querySelector(".test").childNodes[0];
        selection.setBaseAndExtent(textNode, 0, textNode, 0);
        expect(":iframe span:contains('bc')").toHaveClass("o_animate");

        // undo removes the span
        editor.shared.history.undo();
        expect(":iframe span").toHaveCount(0);
    });

    test("change existing animated span with a collapsed selection inside it", async () => {
        const websiteBuilder = await setupWebsiteBuilder(
            `<p class="test">a<span class="o_animated_text o_animate o_anim_fade_in o_animate_preview">bc</span>d</p>`
        );
        const editable = websiteBuilder.getEditableContent();

        // put cursor inside the text in the span
        const textNode = editable.querySelector(".test span").childNodes[0];
        setSelection({ anchorNode: textNode, anchorOffset: 1 });

        // animate is marked active
        await expandToolbar();
        expect("button[title='Animate Text']").toHaveClass("active");
        await contains("button[title='Animate Text']").click();
        expect(":iframe span:contains('bc')").not.toHaveClass("o_anim_rotate_in");
        expect(":iframe span:contains('bc')").toHaveClass("o_anim_fade_in");

        // "reset" removes the animation on the whole span
        await contains("button[title=Reset]").click();
        expect(":iframe span").toHaveCount(0);
        expect(":iframe .test").toHaveText("abcd");
    });

    test("change existing animated span by selecting the exact text", async () => {
        const websiteBuilder = await setupWebsiteBuilder(
            `<p class="test">a<span class="o_animated_text o_animate o_anim_fade_in o_animate_preview">bc</span>d</p>`
        );
        const editable = websiteBuilder.getEditableContent();
        const selection = editable.ownerDocument.getSelection();

        // select the text in the span
        const textNode = editable.querySelector(".test span").childNodes[0];
        selection.setBaseAndExtent(textNode, 0, textNode, 2);

        // animate is marked active
        await expandToolbar();
        expect("button[title='Animate Text']").toHaveClass("active");
        await contains("button[title='Animate Text']").click();
        expect(":iframe span:contains('bc')").not.toHaveClass("o_anim_rotate_in");
        expect(":iframe span:contains('bc')").toHaveClass("o_anim_fade_in");

        // click on an animation effect and it is changed on the span
        await contains("div:has(>div[data-action-value=o_anim_rotate_in]) + button").click();
        await contains("div[data-action-value=o_anim_rotate_in]:not(.d-none *)").click();
        expect(":iframe span:contains('bc')").toHaveClass("o_anim_rotate_in");
        expect(":iframe span:contains('bc')").not.toHaveClass("o_anim_fade_in");

        // undo restore the classes
        await contains("button.fa-undo").click();
        expect(":iframe span:contains('bc')").not.toHaveClass("o_anim_rotate_in");
        expect(":iframe span:contains('bc')").toHaveClass("o_anim_fade_in");

        // reset removes the span
        await contains(":iframe span").click(); // move the selection around to make the toolbar re-appear
        selection.setBaseAndExtent(textNode, 0, textNode, 2);
        await expandToolbar();
        await contains("button[title='Animate Text']").click();
        await contains("button[title=Reset]").click();
        expect(":iframe span").toHaveCount(0);
        expect(":iframe .test").toHaveText("abcd");
    });

    test("clicking on animate when popover is open", async () => {
        const websiteBuilder = await setupWebsiteBuilder(
            `<p class="test">a<span class="o_animated_text">bc</span>d</p>`
        );
        const editable = websiteBuilder.getEditableContent();
        const selection = editable.ownerDocument.getSelection();

        // select the text in the span
        const textNode = editable.querySelector(".test span").childNodes[0];
        selection.setBaseAndExtent(textNode, 0, textNode, 2);

        // animate is marked active
        await expandToolbar();
        expect("button[title='Animate Text']").toHaveClass("active");
        await contains("button[title='Animate Text']").click();
        expect("div[data-class-action=o_animate]").toHaveCount(1);

        await contains("button[title='Animate Text']").click();
        expect("div[data-class-action=o_animate]").toHaveCount(1);
    });

    test("set animation with a selection overlapping existing animated span (start of span in selection)", async () => {
        const websiteBuilder = await setupWebsiteBuilder(
            `<p class="test">a<span class="o_animated_text">bc</span>d</p>`
        );
        const editable = websiteBuilder.getEditableContent();
        const selection = editable.ownerDocument.getSelection();

        const test = editable.querySelector(".test");
        const span = editable.querySelector(".test span");

        selection.setBaseAndExtent(test.childNodes[0], 0, span.childNodes[0], 1);

        await expandToolbar();
        expect("button[title='Animate Text']").not.toHaveClass("active");
        await contains("button[title='Animate Text']").click();
        expect(":iframe span:eq(0)").toHaveText("ab");
        expect(":iframe span:eq(1)").toHaveText("c");
    });

    test("set animation with a selection overlapping existing animated span (end of span in selection)", async () => {
        const websiteBuilder = await setupWebsiteBuilder(
            `<p class="test">a<span class="o_animated_text">bc</span>d</p>`
        );
        const editable = websiteBuilder.getEditableContent();
        const selection = editable.ownerDocument.getSelection();

        const test = editable.querySelector(".test");
        const span = editable.querySelector(".test span");

        selection.setBaseAndExtent(span.childNodes[0], 1, test.childNodes[2], 1);

        await expandToolbar();
        expect("button[title='Animate Text']").not.toHaveClass("active");
        await contains("button[title='Animate Text']").click();
        expect(":iframe span:eq(0)").toHaveText("b");
        expect(":iframe span:eq(1)").toHaveText("cd");
    });

    test("set animation with a selection contained inside an existing animated span", async () => {
        const websiteBuilder = await setupWebsiteBuilder(
            `<p class="test">a<span class="o_animated_text" other-attribute>bcd</span>e</p>`
        );
        const editable = websiteBuilder.getEditableContent();
        const selection = editable.ownerDocument.getSelection();

        const span = editable.querySelector(".test span");

        selection.setBaseAndExtent(span.childNodes[0], 1, span.childNodes[0], 2);

        await expandToolbar();
        expect("button[title='Animate Text']").not.toHaveClass("active");
        await contains("button[title='Animate Text']").click();
        expect(":iframe span[other-attribute]:eq(0)").toHaveText("b");
        expect(":iframe span:not([other-attribute])").toHaveText("c");
        expect(":iframe span[other-attribute]:eq(1)").toHaveText("d");
    });

    test("reset animation with a selection containing and overlapping existing animated spans", async () => {
        const websiteBuilder = await setupWebsiteBuilder(
            `<p class="test">a<span class="o_animated_text">bc</span>d<span class="o_animated_text">ef</span>g<span class="o_animated_text">hi</span>j</p>`
        );
        const editable = websiteBuilder.getEditableContent();
        const selection = editable.ownerDocument.getSelection();

        const test = editable.querySelector(".test");

        selection.setBaseAndExtent(
            test.childNodes[1].childNodes[0],
            1,
            test.childNodes[5].childNodes[0],
            1
        );

        await expandToolbar();
        expect("button[title='Animate Text']").not.toHaveClass("active");
        await contains("button[title='Animate Text']").click();
        expect(":iframe span:eq(0)").toHaveText("b");
        expect(":iframe span:eq(1)").toHaveText("cdefgh");
        expect(":iframe span:eq(2)").toHaveText("i");

        // click reset to remove the selected span
        await contains("button[title=Reset]").click();
        expect(":iframe span:eq(0)").toHaveText("b");
        expect(":iframe span:eq(1)").toHaveText("i");
        expect(":iframe .test").toHaveText("abcdefghij");
    });

    test("tool is active when text in span is selected even if there are unselected empty node at the end", async () => {
        await setupWebsiteBuilder(
            `<p class="test">a<span class="o_animated_text">bc<svg/></span>d</p>`
        );
        const span = queryOne(":iframe span");
        setSelection({ anchorNode: span, anchorOffset: 0, focusNode: span, focusOffset: 1 });
        await expandToolbar();
        expect("button[title='Animate Text']").toHaveClass("active");
    });

    test("Applied animation from floating toolbar should not reset", async () => {
        await setupWebsiteBuilder(`<div>
            <h5>About us</h5>
            <p>We are a team of passionate people whose goal is to improve everyone's life through disruptive products. We build great products to solve your business problems.
            <br><br>Our products are designed for small to medium size companies willing to optimize their performance.</p>
        </div>`);
        const paragraphEl = queryOne(":iframe p");
        setSelection({
            anchorNode: paragraphEl.firstChild,
            anchorOffset: 0,
            focusNode: paragraphEl.lastChild,
            focusOffset: paragraphEl.lastChild.length,
        });
        await waitFor(".o-we-toolbar");
        await expandToolbar();

        // Apply text highlight from the floating toolbar.
        await contains(".o-we-toolbar button[title='Apply highlight']").click();
        await contains(".o_popover .o_text_highlight_underline").click();

        // Reselect all the text in the paragraph and reopen toolbar.
        await thirdClick(paragraphEl);
        await advanceTime(500);
        await waitFor(".o-we-toolbar");
        await expandToolbar();

        // Apply the default animation to the selected text.
        await contains(".o-we-toolbar button[title='Animate Text']").click();

        // Reselect all the text again and verify animate button remains active.
        await thirdClick(paragraphEl);
        await advanceTime(500);
        await waitFor(".o-we-toolbar");
        await expandToolbar();

        expect("button[title='Animate Text']").toHaveClass("active");
    });
});
