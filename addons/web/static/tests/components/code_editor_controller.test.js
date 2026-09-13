// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { AceEditorController } from "@web/components/code_editor/ace_editor_hook";

describe.current.tags("headless");

function makeAce() {
    /** @type {any[]} */
    const log = [];
    class Session {
        constructor(value = "") {
            this.value = value;
            /** @type {any[]} */
            this.handlers = [];
            this.options = null;
            this.mode = null;
        }
        getValue() {
            return this.value;
        }
        setValue(/** @type {any} */ value) {
            this.value = value;
            for (const handler of this.handlers) {
                handler();
            }
        }
        on(/** @type {any} */ _event, /** @type {any} */ handler) {
            this.handlers.push(handler);
        }
        setUndoManager() {}
        setOptions(/** @type {any} */ options) {
            this.options = options;
        }
        setMode(/** @type {any} */ mode) {
            this.mode = mode;
        }
        destroy() {
            log.push("session destroyed");
        }
    }
    const editor = {
        session: new Session("initial"),
        cursor: { row: 0, column: 0 },
        renderer: {
            setOptions: () => {},
            $cursorLayer: { element: { style: {} } },
            scrollCursorIntoView: () => log.push("scrolled"),
        },
        selection: {
            moveToPosition: (/** @type {any} */ pos) =>
                log.push(`moved ${pos.row}:${pos.column}`),
        },
        getSession() {
            return this.session;
        },
        setSession(/** @type {any} */ session) {
            this.session = session;
            log.push("session switched");
        },
        getValue() {
            return this.session.getValue();
        },
        getCursorPosition() {
            return this.cursor;
        },
        setOptions: () => {},
        setTheme: (/** @type {any} */ theme) => log.push(`theme ${theme}`),
        on: () => {},
        focus: () => log.push("focused"),
        destroy: () => log.push("editor destroyed"),
    };
    patchWithCleanup(window, {
        ace: {
            edit: () => editor,
            EditSession: Session,
            UndoManager: class {},
        },
    });
    return { editor, log };
}

/** @param {Partial<Record<string, any>>} [overrides] */
function makeController(overrides = {}) {
    /** @type {any[]} */
    const changes = [];
    const controller = new AceEditorController({
        ref: { el: null },
        getValue: () => "initial",
        getSessionId: () => "a",
        getMode: () => "python",
        getTheme: () => "",
        isReadonly: () => false,
        showLineNumbers: () => true,
        getMaxLines: () => undefined,
        onChange: (value) => changes.push(value),
        ...overrides,
    });
    return { controller, changes };
}

test("a session is created once per id and reused", () => {
    makeAce();
    const { controller } = makeController();
    controller.attach(document.createElement("div"));

    const first = controller.acquireSession("b");
    expect(controller.acquireSession("b")).toBe(first);
    expect(controller.acquireSession("c")).not.toBe(first);
});

test("attach adopts Ace's own session rather than opening a second one", () => {
    const { editor } = makeAce();
    const { controller } = makeController();
    controller.attach(document.createElement("div"));

    expect(controller.sessions["a"]).toBe(editor.session);
});

test("a programmatic value sync is not reported back as an edit", () => {
    makeAce();
    const { controller, changes } = makeController();
    controller.attach(document.createElement("div"));
    expect(changes).toEqual([]);

    controller.syncValue("a", "from the outside");
    expect(changes).toEqual([]);
    expect(controller.sessions["a"].getValue()).toBe("from the outside");

    controller.sessions["a"].handlers.at(-1)();
    expect(changes).toEqual(["from the outside"]);
});

test("syncing a value that already matches touches nothing", () => {
    makeAce();
    const { controller } = makeController();
    controller.attach(document.createElement("div"));
    const session = controller.sessions["a"];
    session.value = "same";

    controller.syncValue("a", "same");
    expect(session.getValue()).toBe("same");
    expect(controller.ignoreAceChange).toBe(false);
});

test("detach destroys the editor and every session it opened", () => {
    const { log } = makeAce();
    const { controller } = makeController();
    const teardown = controller.attach(document.createElement("div"));
    controller.acquireSession("b");

    teardown();
    expect(controller.editor).toBe(null);
    expect(controller.sessions).toEqual({});
    expect(log.filter((entry) => entry === "session destroyed")).toHaveLength(2);
    expect(log).toInclude("editor destroyed");
});

test("options and theme are inert before an editor exists", () => {
    makeAce();
    const { controller } = makeController();
    expect(() => controller.applyTheme("monokai")).not.toThrow();
    expect(() => controller.applyOptions(true, false, 10)).not.toThrow();
    expect(() => controller.showSession("a", "xml")).not.toThrow();
    expect(() => controller.syncValue("a", "x")).not.toThrow();
    expect(() => controller.placeCursor({ row: 1, column: 2 })).not.toThrow();
});

for (const id of ["constructor", "toString", "__proto__"]) {
    test(`session id ${id} adopts and reuses its owned Ace session`, () => {
        const { editor, log } = makeAce();
        const { controller } = makeController({ getSessionId: () => id });
        const teardown = controller.attach(document.createElement("div"));
        expect(controller.acquireSession(id)).toBe(editor.session);
        expect(() => controller.showSession(id, "xml")).not.toThrow();
        teardown();
        expect(log.filter((entry) => entry === "session destroyed")).toHaveLength(1);
        expect(() =>
            controller.acquireSession(id).setMode("ace/mode/python"),
        ).not.toThrow();
        controller.detach();
    });
}
