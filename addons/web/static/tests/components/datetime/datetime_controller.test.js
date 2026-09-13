// @ts-check

import { beforeEach, expect, getFixture, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { DateTimePickerController } from "@web/components/datetime/datetime_picker_service";
import { localization } from "@web/core/l10n/localization";
import { luxon } from "@web/core/l10n/luxon";

const { DateTime } = luxon;

test("applying the same pending value waits for its save", async () => {
    const saved = new Deferred();
    const { controller } = createController({
        pickerProps: { type: "date", value: DateTime.fromSQL("2023-07-07") },
        onApply: () => {
            expect.step("save");
            return saved;
        },
    });
    const first = controller.apply();
    let finished = false;
    const second = controller.apply().then(() => {
        finished = true;
    });
    await Promise.resolve();
    await Promise.resolve();
    expect(finished).toBe(false);
    expect.verifySteps(["save"]);
    saved.resolve();
    await Promise.all([first, second]);
    expect(finished).toBe(true);
});

test("a failed apply can retry the same value", async () => {
    let attempts = 0;
    const failure = new Error("save rejected");
    const { controller } = createController({
        pickerProps: { type: "date", value: DateTime.fromSQL("2023-07-07") },
        onApply: async () => {
            attempts++;
            if (attempts === 1) {
                throw failure;
            }
        },
    });
    let error;
    try {
        await controller.apply();
    } catch (caught) {
        error = caught;
    }
    expect(error).toBe(failure);
    await controller.apply();
    expect(attempts).toBe(2);
    await controller.apply();
    expect(attempts).toBe(2);
});

beforeEach(() => {
    patchWithCleanup(localization, {
        dateFormat: "MM/dd/yyyy",
        dateTimeFormat: "MM/dd/yyyy HH:mm:ss",
    });
});

/** @param {{ onClose?: () => any }} options */
function makeFakePopover(options) {
    let open = false;
    return {
        lastTarget: /** @type {any} */ (null),
        lastProps: /** @type {any} */ (null),
        open(/** @type {any} */ target, /** @type {any} */ props) {
            this.lastTarget = target;
            this.lastProps = props;
            open = true;
        },
        close() {
            if (open) {
                open = false;
                options.onClose?.();
            }
        },
        get isOpen() {
            return open;
        },
    };
}

/**
 * @param {Record<string, any>} [params]
 * @param {{ dateTimePickerList?: Set<any> }} [opts]
 */
function createController(params = {}, opts = {}) {
    const dateTimePickerList = opts.dateTimePickerList || new Set();
    const env = { isSmall: false };
    /** @type {any} */
    let popover;
    const fullParams = {
        createPopover: (/** @type {any} */ _component, /** @type {any} */ options) => {
            popover = makeFakePopover(options);
            return popover;
        },
        ...params,
    };
    const controller = new DateTimePickerController(
        fullParams,
        env,
        null,
        dateTimePickerList,
    );
    return { controller, dateTimePickerList, getPopover: () => popover };
}

/** @param {number} count */
function makeInputs(count = 1) {
    const fixture = getFixture();
    const inputs = [];
    for (let i = 0; i < count; i++) {
        const input = document.createElement("input");
        input.type = "text";
        fixture.appendChild(input);
        inputs.push(input);
    }
    return inputs;
}

test("updateInput formats a value into the input and clears on falsy", () => {
    const [input] = makeInputs(1);
    const { controller } = createController({
        getInputs: () => [input],
        pickerProps: { type: "date", value: false },
    });

    controller.updateInput(input, DateTime.fromSQL("2023-06-06"));
    expect(input.value).toBe("06/06/2023");

    controller.updateInput(input, false);
    expect(input.value).toBe("");
});

test("enable() syncs inputs and wires listeners; disable removes them", () => {
    const [input] = makeInputs(1);
    const { controller } = createController({
        getInputs: () => [input],
        pickerProps: { type: "date", value: DateTime.fromSQL("2023-06-06") },
    });

    const removeListeners = controller.enable();
    expect(input.value).toBe("06/06/2023");
    expect(controller.disableListeners).toBe(removeListeners);

    input.dispatchEvent(new Event("click"));
    expect(controller.isOpen()).toBe(true);
    controller.saveAndClose();
    expect(controller.isOpen()).toBe(false);

    removeListeners();
    expect(controller.disableListeners).toBe(null);
    input.dispatchEvent(new Event("click"));
    expect(controller.isOpen()).toBe(false);
});

test("pickerProps.tz drives the input's zone for both format and parse", () => {
    const [input] = makeInputs(1);
    const { controller } = createController({
        getInputs: () => [input],
        pickerProps: {
            type: "datetime",
            value: DateTime.fromISO("2023-06-06T12:00:00", { zone: "UTC" }),
            tz: "Asia/Tokyo",
        },
    });

    controller.updateInput(
        input,
        DateTime.fromISO("2023-06-06T12:00:00", { zone: "UTC" }),
    );
    expect(input.value).toBe("06/06/2023 21:00:00");

    input.value = "06/06/2023 21:00:00";
    controller.updateValueFromInputs();
    expect(controller.pickerProps.value.toUTC().toISO()).toBe(
        "2023-06-06T12:00:00.000Z",
    );
});

test("updateValueFromInputs parses inputs into state and notifies onChange", () => {
    const [input] = makeInputs(1);
    const onChange = (/** @type {any} */ v) =>
        expect.step(`change:${v ? v.toISODate() : v}`);
    const { controller } = createController({
        getInputs: () => [input],
        onChange,
        pickerProps: { type: "date", value: false },
    });

    input.value = "07/07/2023";
    controller.updateValueFromInputs();

    expect(controller.pickerProps.value.toISODate()).toBe("2023-07-07");
    expect.verifySteps(["change:2023-07-07"]);

    input.value = "not a date";
    controller.updateValueFromInputs();
    expect(controller.pickerProps.value.toISODate()).toBe("2023-07-07");
    expect(input.value).toBe("07/07/2023");
    expect.verifySteps([]);
});

test("open()/close() drive the popover with the reactive pickerProps", () => {
    const [input] = makeInputs(1);
    const { controller, getPopover } = createController({
        target: input,
        getInputs: () => [input],
        pickerProps: { type: "date", value: false },
    });

    expect(controller.isOpen()).toBe(false);

    controller.open(0);
    expect(controller.isOpen()).toBe(true);
    expect(controller.pickerProps.focusedDateIndex).toBe(0);
    expect(getPopover().lastTarget).toBe(input);
    expect(getPopover().lastProps.pickerProps).toBe(controller.pickerProps);

    controller.picker.close();
    expect(controller.isOpen()).toBe(false);
});

test("open() closes other pickers sharing the service registry", () => {
    const list = new Set();
    const [inputA] = makeInputs(1);
    const [inputB] = makeInputs(1);
    const a = createController(
        {
            target: inputA,
            getInputs: () => [inputA],
            pickerProps: { type: "date", value: false },
        },
        { dateTimePickerList: list },
    );
    const b = createController(
        {
            target: inputB,
            getInputs: () => [inputB],
            pickerProps: { type: "date", value: false },
        },
        { dateTimePickerList: list },
    );

    a.controller.open(0);
    expect(a.controller.isOpen()).toBe(true);

    b.controller.open(0);
    expect(b.controller.isOpen()).toBe(true);
    expect(a.controller.isOpen()).toBe(false);
});

test("apply() fires onApply only when the value actually changed", async () => {
    const [input] = makeInputs(1);
    const onApply = (/** @type {any} */ v) =>
        expect.step(`apply:${v ? v.toISODate() : v}`);
    const { controller } = createController({
        getInputs: () => [input],
        onApply,
        pickerProps: { type: "date", value: false },
    });

    controller.pickerProps.value = DateTime.fromSQL("2023-07-07");
    await controller.apply();
    expect.verifySteps(["apply:2023-07-07"]);

    await controller.apply();
    expect.verifySteps([]);

    controller.pickerProps.value = DateTime.fromSQL("2023-08-08");
    await controller.apply();
    expect.verifySteps(["apply:2023-08-08"]);
});

test("onSelect marks the value and applies for a single date picker", async () => {
    const [input] = makeInputs(1);
    const onChange = (/** @type {any} */ v) =>
        expect.step(`change:${v ? v.toISODate() : v}`);
    const onApply = (/** @type {any} */ v) =>
        expect.step(`apply:${v ? v.toISODate() : v}`);
    const { controller } = createController({
        getInputs: () => [input],
        onChange,
        onApply,
        pickerProps: { type: "date", value: false },
    });

    await controller.pickerProps.onSelect(DateTime.fromSQL("2023-09-09"), "date");

    expect(controller.pickerProps.value.toISODate()).toBe("2023-09-09");
    expect.verifySteps(["change:2023-09-09", "apply:2023-09-09"]);
});

test("dispose() tears down: closes popover, removes listeners, releases registry, guards apply (F1)", async () => {
    const list = new Set();
    const [input] = makeInputs(1);
    const onApply = (/** @type {any} */ v) => expect.step(`apply:${v}`);
    const { controller } = createController(
        {
            target: input,
            getInputs: () => [input],
            onApply,
            pickerProps: { type: "date", value: false },
        },
        { dateTimePickerList: list },
    );

    controller.enable();
    controller.open(0);
    expect(controller.isOpen()).toBe(true);
    expect(list.has(controller.picker)).toBe(true);

    controller.dispose();

    expect(controller.destroyed).toBe(true);
    expect(controller.isOpen()).toBe(false);
    expect(controller.disableListeners).toBe(null);
    expect(list.has(controller.picker)).toBe(false);

    controller.pickerProps.value = DateTime.fromSQL("2024-01-01");
    await controller.apply();
    expect.verifySteps([]);
});

test("constructor tolerates an absent pickerProps (F13)", () => {
    let controller;
    expect(() => {
        controller = createController({
            getInputs: () => /** @type {any[]} */ ([]),
        }).controller;
    }).not.toThrow();
    expect(/** @type {any} */ (controller).pickerProps.type).toBe("datetime");
});

test("getPopoverTarget range mode falls back when the first input is disconnected (F14)", () => {
    const input0 = document.createElement("input");
    const [input1] = makeInputs(1);
    const { controller } = createController({
        getInputs: () => [input0, input1],
        pickerProps: { type: "date", range: true, value: [false, false] },
    });

    expect(controller.getPopoverTarget()).toBe(input1);
});

test("the visibility spacer borrowed from the target is returned on dispose", () => {
    const [input] = makeInputs(1);
    input.style.marginBottom = "4px";
    const { controller } = createController({
        target: input,
        getInputs: () => [input],
        ensureVisibility: () => true,
        pickerProps: { type: "date", value: false },
    });

    controller.enable();
    controller.open(0);
    expect(input.style.marginBottom).toBe("100vh");

    controller.dispose();
    expect(input.style.marginBottom).toBe("4px");
});

test("the visibility spacer is returned on a normal close", () => {
    const [input] = makeInputs(1);
    input.style.marginBottom = "4px";
    const { controller } = createController({
        target: input,
        getInputs: () => [input],
        ensureVisibility: () => true,
        pickerProps: { type: "date", value: false },
    });

    controller.enable();
    controller.open(0);
    expect(input.style.marginBottom).toBe("100vh");

    controller.picker.close();
    expect(input.style.marginBottom).toBe("4px");
});

test("dispose runs every teardown step even when one throws", async () => {
    const { controller, dateTimePickerList, getPopover } = createController();
    const [input] = makeInputs(1);
    controller.getInputs = () => [input, null];
    controller.enable();
    controller.open(0);
    expect(controller.isOpen()).toBe(true);
    expect(dateTimePickerList.has(controller.picker)).toBe(true);

    patchWithCleanup(getPopover(), {
        close() {
            throw new Error("popover close blew up");
        },
    });

    /** @type {any} */
    let raised = null;
    try {
        controller.dispose();
    } catch (error) {
        raised = error;
    }

    expect(raised?.message).toBe("popover close blew up");
    expect(dateTimePickerList.has(controller.picker)).toBe(false);
    expect(controller.disableListeners).toBe(null);
    expect(controller.destroyed).toBe(true);
});

test("unregister only drops the registration, it is not enable's inverse", async () => {
    const { controller, dateTimePickerList } = createController();
    const [input] = makeInputs(1);
    controller.getInputs = () => [input, null];
    controller.enable();

    expect(dateTimePickerList.has(controller.picker)).toBe(true);
    controller.picker.unregister();
    expect(dateTimePickerList.has(controller.picker)).toBe(false);
    expect(controller.disableListeners).not.toBe(null);
});

test("reverting to the saved value while another save is pending applies the revert", async () => {
    const saved = new Deferred();
    const a = DateTime.fromSQL("2023-07-07");
    const b = DateTime.fromSQL("2023-08-08");
    const { controller, getPopover } = createController({
        pickerProps: { type: "date", value: a },
        onApply: (value) => {
            expect.step(value.toISODate());
            if (value === b) {
                return saved;
            }
        },
    });
    getPopover().open(document.body, {});
    await controller.apply();
    controller.pickerProps.value = b;
    const pending = controller.apply();
    controller.pickerProps.value = a;
    await controller.apply();
    expect.verifySteps(["2023-07-07", "2023-08-08", "2023-07-07"]);
    saved.resolve();
    await pending;
    await controller.apply();
    expect.verifySteps([]);
});

test("an older failed save does not release the newer pending save", async () => {
    const firstSaved = new Deferred();
    const secondSaved = new Deferred();
    const a = DateTime.fromSQL("2023-07-07");
    const b = DateTime.fromSQL("2023-08-08");
    const { controller, getPopover } = createController({
        pickerProps: { type: "date", value: a },
        onApply: (value) => {
            expect.step(value.toISODate());
            return value === a ? firstSaved : secondSaved;
        },
    });
    getPopover().open(document.body, {});
    const first = controller.apply().catch(() => {});
    controller.pickerProps.value = b;
    const second = controller.apply();
    firstSaved.reject(new Error("older save failed"));
    await first;
    let finished = false;
    const repeated = controller.apply().then(() => {
        finished = true;
    });
    await Promise.resolve();
    await Promise.resolve();
    expect(finished).toBe(false);
    expect.verifySteps(["2023-07-07", "2023-08-08"]);
    secondSaved.resolve();
    await Promise.all([second, repeated]);
    expect(finished).toBe(true);
});
