// @ts-check

import { expect, test } from "@odoo/hoot";
import { queryAllTexts, setInputFiles } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import {
    contains,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { NameAndSignature } from "@web/components/signature/name_and_signature";

const TINY_PNG =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+BCQAHBQICJmhD1AAAAABJRU5ErkJggg==";

for (const action of ["clear", "switch mode", "destroy"]) {
    test(`pending image decoding cannot undo ${action}`, async () => {
        const component = await mountWithCleanup(NameAndSignature, {
            props: { signature: { name: "Owner" }, mode: "draw" },
        });
        const decoded = new Deferred();
        patchWithCleanup(HTMLImageElement.prototype, { decode: () => decoded });
        patchWithCleanup(component.signaturePad.canvas.getContext("2d"), {
            drawImage: () => expect.step("paint"),
        });
        const pending = component.printImage(TINY_PNG);
        if (action === "clear") {
            component.clear();
        } else if (action === "switch mode") {
            component.setMode("load");
        } else {
            component.__owl__.app.destroy();
        }
        decoded.resolve();
        await pending;
        expect.verifySteps([]);
        expect(component.props.signature.isSignatureEmpty).toBe(true);
    });
}

const getNameAndSignatureButtonNames = () =>
    queryAllTexts(".card-header .col-auto").filter(
        (/** @type {any} */ text) => text.length,
    );

onRpc("/web/sign/get_fonts/", () => ({}));

test("test name_and_signature widget", async () => {
    const props = {
        signature: {
            name: "Don Toliver",
        },
    };
    await mountWithCleanup(NameAndSignature, { props });
    expect(getNameAndSignatureButtonNames()).toEqual(["Auto", "Draw", "Load"]);
    expect(".o_web_sign_auto_select_style").toHaveCount(1);
    expect(".card-header .active").toHaveCount(1);
    expect(".card-header .active").toHaveText("Auto");
    expect(".o_web_sign_name_group input").toHaveCount(1);
    expect(".o_web_sign_name_group input").toHaveValue("Don Toliver");

    await contains(".o_web_sign_draw_button").click();
    expect(getNameAndSignatureButtonNames()).toEqual(["Auto", "Draw", "Load"]);
    expect(".o_web_sign_draw_clear").toHaveCount(1);
    expect(".card-header .active").toHaveCount(1);
    expect(".card-header .active").toHaveText("Draw");

    await contains(".o_web_sign_load_button").click();
    expect(getNameAndSignatureButtonNames()).toEqual(["Auto", "Draw", "Load"]);
    expect(".o_web_sign_load_file").toHaveCount(1);
    expect(".card-header .active").toHaveCount(1);
    expect(".card-header .active").toHaveText("Load");
});

test("test name_and_signature widget without name", async () => {
    await mountWithCleanup(NameAndSignature, { props: { signature: {} } });
    expect(".card-header").toHaveCount(0);
    expect(".o_web_sign_name_group input").toHaveCount(1);
    expect(".o_web_sign_name_group input").toHaveValue("");

    await contains(".o_web_sign_name_group input").fill("plop", { instantly: true });
    expect(getNameAndSignatureButtonNames()).toEqual(["Auto", "Draw", "Load"]);
    expect(".o_web_sign_auto_select_style").toHaveCount(1);
    expect(".card-header .active").toHaveText("Auto");
    expect(".o_web_sign_name_group input").toHaveCount(1);
    expect(".o_web_sign_name_group input").toHaveValue("plop");

    await contains(".o_web_sign_draw_button").click();
    expect(".card-header .active").toHaveCount(1);
    expect(".card-header .active").toHaveText("Draw");
});

test("test name_and_signature widget with noInputName and default name", async function () {
    const props = {
        signature: {
            name: "Don Toliver",
        },
        noInputName: true,
    };
    await mountWithCleanup(NameAndSignature, { props });
    expect(getNameAndSignatureButtonNames()).toEqual(["Auto", "Draw", "Load"]);
    expect(".o_web_sign_auto_select_style").toHaveCount(1);
    expect(".card-header .active").toHaveCount(1);
    expect(".card-header .active").toHaveText("Auto");
});

test("test name_and_signature widget with noInputName and without name", async function () {
    const props = {
        signature: {},
        noInputName: true,
    };
    await mountWithCleanup(NameAndSignature, { props });
    expect(getNameAndSignatureButtonNames()).toEqual(["Draw", "Load"]);
    expect(".o_web_sign_draw_clear").toHaveCount(1);
    expect(".card-header .active").toHaveCount(1);
    expect(".card-header .active").toHaveText("Draw");
});

test("test name_and_signature widget default signature", async function () {
    const props = {
        signature: {
            name: "Brandon Freeman",
            signatureImage:
                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+BCQAHBQICJmhD1AAAAABJRU5ErkJggg==",
        },
        mode: "draw",
        signatureType: "signature",
        noInputName: true,
    };
    const res = await mountWithCleanup(NameAndSignature, { props });
    expect(res.isSignatureEmpty).toBe(false);
    expect(res.props.signature.isSignatureEmpty).toBe(false);
});

test("test name_and_signature widget update signmode with onSignatureChange prop", async function () {
    let currentSignMode = "";
    const props = {
        signature: { name: "Test Owner" },
        onSignatureChange: function (/** @type {string} */ signMode) {
            if (currentSignMode !== signMode) {
                currentSignMode = signMode;
            }
        },
    };
    await mountWithCleanup(NameAndSignature, { props });
    await contains(".o_web_sign_draw_button").click();
    expect(currentSignMode).toBe("draw");
});

test("test name_and_signature widget with non-breaking spaces", async function () {
    const props = {
        signature: { name: "Non Breaking Spaces" },
    };
    const res = await mountWithCleanup(NameAndSignature, { props });
    expect(res.getCleanedName()).toBe("Non Breaking Spaces");
});

test("test name_and_signature widget with non-breaking spaces and initials mode", async function () {
    const props = {
        signature: { name: "Non Breaking Spaces" },
        signatureType: "initial",
    };
    const res = await mountWithCleanup(NameAndSignature, { props });
    expect(res.getCleanedName()).toBe("N.B.S.");
});

test("printImage serializes concurrent calls with KeepLast (only the last draws)", async () => {
    const res = await mountWithCleanup(NameAndSignature, {
        props: {
            signature: { name: "Test Owner" },
            mode: "draw",
        },
    });

    const ctx = res.signaturePad.canvas.getContext("2d");
    patchWithCleanup(ctx, {
        drawImage() {
            expect.step("drawImage");
            return super.drawImage(...arguments);
        },
    });

    const first = res.printImage(TINY_PNG);
    const second = res.printImage(TINY_PNG);

    await Promise.all([first, second]);
    await animationFrame();

    expect.verifySteps(["drawImage"]);
});

test("a signature model handed over without a name is normalised, not crashed on", async () => {
    for (const name of [null, undefined, ""]) {
        /** @type {any} */
        const signature = { name };
        await mountWithCleanup(NameAndSignature, { props: { signature } });
        await animationFrame();
        expect(signature.name).toBe("");
        expect(".o_web_sign_name_input").toHaveValue("");
    }
});

test("an auto-drawn name counts as a signature, and clearing it does not", async () => {
    const props = {
        /** @type {{ name: string, isSignatureEmpty?: boolean }} */
        signature: { name: "Brandon Freeman" },
        mode: "auto",
        signatureType: "signature",
        noInputName: true,
    };
    const component = await mountWithCleanup(NameAndSignature, { props });
    await animationFrame();

    expect(component.signaturePad.isEmpty()).toBe(true, {
        message: "the pad itself cannot see a canvas painted behind its back",
    });
    expect(component.isSignatureEmpty).toBe(false);
    expect(/** @type {any} */ (props.signature).isSignatureEmpty).toBe(false);

    component.clear();
    expect(component.isSignatureEmpty).toBe(true);
    expect(/** @type {any} */ (props.signature).isSignatureEmpty).toBe(true);
});

test("loading a file that is not an image says so", async () => {
    await mountWithCleanup(NameAndSignature, { props: { signature: { name: "Don" } } });
    await contains(".o_web_sign_load_button").click();
    expect(".o_web_sign_load_invalid").toHaveCount(0);

    await contains(".o_web_sign_load_file input", { visible: false }).click();
    await setInputFiles([
        new File(["not an image"], "notes.txt", { type: "text/plain" }),
    ]);
    await animationFrame();

    expect(".o_web_sign_load_invalid").toHaveCount(1);
    expect(".o_web_sign_load_invalid").toBeVisible();
});

for (const action of ["clear", "switch mode", "destroy"]) {
    test(`a pending file read cannot undo ${action}`, async () => {
        const component = await mountWithCleanup(NameAndSignature, {
            props: { signature: { name: "Owner" }, mode: "draw" },
        });
        const captured = /** @type {{ reader?: FileReader }} */ ({});
        patchWithCleanup(FileReader.prototype, {
            readAsDataURL() {
                captured.reader = this;
            },
        });
        patchWithCleanup(HTMLImageElement.prototype, { decode: async () => {} });
        patchWithCleanup(component.signaturePad.canvas.getContext("2d"), {
            drawImage: () => expect.step("paint"),
        });
        // @ts-expect-error Exercise the private input handler while its file read is pending.
        const pending = component.onChangeSignLoadInput(
            /** @type {any} */ ({
                target: {
                    files: [
                        new File(["image"], "signature.png", { type: "image/png" }),
                    ],
                    value: "",
                },
            }),
        );
        if (action === "clear") {
            component.clear();
        } else if (action === "switch mode") {
            component.setMode("load");
        } else {
            component.__owl__.app.destroy();
        }
        const reader = captured.reader;
        if (!reader) {
            throw new Error("The input handler did not start a file read");
        }
        Object.defineProperty(reader, "result", { value: TINY_PNG });
        reader.dispatchEvent(new Event("load"));
        await pending;
        expect.verifySteps([]);
        expect(component.props.signature.isSignatureEmpty).toBe(true);
    });
}

test("restoring an image cannot paint after clear", async () => {
    const component = await mountWithCleanup(NameAndSignature, {
        props: { signature: { name: "Owner" }, mode: "draw" },
    });
    const decoded = new Deferred();
    const captured =
        /** @type {{ image?: { width: number, height: number, onload?: () => void } }} */ ({});
    patchWithCleanup(window, {
        Image: /** @type {any} */ (
            class {
                constructor() {
                    captured.image = this;
                }
                width = 1;
                height = 1;
                decode() {
                    return decoded;
                }
            }
        ),
    });
    patchWithCleanup(component.signaturePad.canvas.getContext("2d"), {
        drawImage: () => expect.step("paint"),
    });
    const pending = component.fromDataURL(TINY_PNG);
    component.clear();
    const image = captured.image;
    if (!image) {
        throw new Error("Restoring the signature did not create an image");
    }
    image.onload?.();
    decoded.resolve();
    await pending;
    expect.verifySteps([]);
    expect(component.props.signature.isSignatureEmpty).toBe(true);
});

test("restoring a decoded image paints it and exposes a nonempty signature", async () => {
    const component = await mountWithCleanup(NameAndSignature, {
        props: { signature: { name: "Owner" }, mode: "draw" },
    });
    const source = document.createElement("canvas");
    source.width = 2;
    source.height = 1;
    const sourceContext = source.getContext("2d");
    sourceContext.fillStyle = "rgb(12, 34, 56)";
    sourceContext.fillRect(0, 0, 2, 1);
    await component.fromDataURL(source.toDataURL());
    const canvas = component.signaturePad.canvas;
    const pixel = canvas
        .getContext("2d")
        .getImageData(canvas.width / 2, canvas.height / 2, 1, 1).data;
    expect(Array.from(pixel)).toEqual([12, 34, 56, 255]);
    expect(component.props.signature.isSignatureEmpty).toBe(false);
    component.clear();
    expect(component.props.signature.isSignatureEmpty).toBe(true);
});

test("a newer upload wins even when the older file finishes reading last", async () => {
    const component = await mountWithCleanup(NameAndSignature, {
        props: { signature: { name: "Owner" }, mode: "draw" },
    });
    const readers = [];
    patchWithCleanup(FileReader.prototype, {
        readAsDataURL() {
            readers.push(this);
        },
    });
    patchWithCleanup(HTMLImageElement.prototype, { decode: async () => {} });
    patchWithCleanup(component.signaturePad.canvas.getContext("2d"), {
        drawImage: (image) => expect.step(image.src),
    });
    const event = /** @type {any} */ ({
        target: {
            files: [new File(["image"], "signature.png", { type: "image/png" })],
            value: "",
        },
    });
    const onInput = Reflect.get(component, "onChangeSignLoadInput").bind(component);
    const first = onInput(event);
    const second = onInput(event);
    Object.defineProperty(readers[1], "result", { value: TINY_PNG + "#new" });
    readers[1].dispatchEvent(new Event("load"));
    await second;
    Object.defineProperty(readers[0], "result", { value: TINY_PNG + "#old" });
    readers[0].dispatchEvent(new Event("load"));
    await first;
    expect.verifySteps([TINY_PNG + "#new"]);
});

test("a name signed while the canvas is hidden is empty until the canvas is laid out", async () => {
    const component = await mountWithCleanup(NameAndSignature, {
        props: { signature: { name: "Owner" }, mode: "auto", noInputName: true },
    });
    const canvas = component.signaturePad.canvas;
    canvas.style.display = "none";
    await animationFrame();
    await animationFrame();
    expect([canvas.width, canvas.height]).toEqual([0, 0]);
    expect(component.props.signature.isSignatureEmpty).toBe(true);

    canvas.style.display = "";
    await animationFrame();
    await animationFrame();
    expect(canvas.width).toBeGreaterThan(0);
    expect(component.props.signature.isSignatureEmpty).toBe(false);
    expect(component.props.signature.getSignatureImage()).not.toBe("data:,");
});

test("resizing the canvas keeps the drawn strokes", async () => {
    const component = await mountWithCleanup(NameAndSignature, {
        props: { signature: { name: "Owner" }, mode: "draw" },
    });
    const canvas = component.signaturePad.canvas;
    const strokes = [
        {
            penColor: "black",
            dotSize: 0,
            minWidth: 2,
            maxWidth: 2,
            velocityFilterWeight: 0.7,
            compositeOperation: "source-over",
            points: [10, 20, 30, 40, 50].map((x, time) => ({
                x,
                y: x / 2,
                pressure: 0.5,
                time,
            })),
        },
    ];
    component.signaturePad.fromData(strokes);
    canvas.style.width = "200px";
    await animationFrame();
    await animationFrame();
    expect(canvas.width).toBe(200);
    expect(component.signaturePad.toData()).toEqual(strokes);
    expect(component.props.signature.isSignatureEmpty).toBe(false);
});
