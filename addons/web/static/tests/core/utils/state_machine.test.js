// @ts-check

import { describe, expect, test } from "@odoo/hoot";
import { InvalidTransitionError, StateMachine } from "@web/core/utils/state_machine";

describe.current.tags("headless");

const TRANSITIONS = {
    idle: { begin: "running" },
    running: { ok: "idle", fail: "broken" },
    broken: { reset: "idle" },
};

class InvalidProbeTransitionError extends InvalidTransitionError {
    /**
     * @param {string} from
     * @param {string} event
     */
    constructor(from, event) {
        super("InvalidProbeTransitionError", "ProbeMachine", from, event);
    }
}

class ProbeMachine extends StateMachine {
    static transitions = TRANSITIONS;
    static invalidTransitionError = InvalidProbeTransitionError;
    status = "idle";
}

test("a declared transition moves the status", () => {
    const m = new ProbeMachine();
    expect(m.status).toBe("idle");
    m._transition("begin");
    expect(m.status).toBe("running");
    m._transition("ok");
    expect(m.status).toBe("idle");
});

test("prototype members are not declared events or source states", () => {
    const machine = new ProbeMachine();
    for (const event of ["toString", "constructor", "__proto__"]) {
        expect(() => machine._transition(event)).toThrow(InvalidProbeTransitionError);
        expect(machine.status).toBe("idle");
    }
    machine.status = "__proto__";
    expect(() => machine._transition("toString")).toThrow(InvalidProbeTransitionError);
    expect(machine.status).toBe("__proto__");
});

test("explicitly declared prototype-shaped names remain valid", () => {
    class NamedMachine extends StateMachine {
        static transitions = { ["__proto__"]: { constructor: "done" } };
        status = "__proto__";
    }
    const machine = new NamedMachine();
    machine._transition("constructor");
    expect(machine.status).toBe("done");
});

test("an undeclared event throws the subclass's error and leaves the status put", () => {
    const m = new ProbeMachine();
    let caught;
    try {
        m._transition("ok");
    } catch (error) {
        caught = error;
    }
    expect(caught).toBeInstanceOf(InvalidProbeTransitionError);
    expect(caught).toBeInstanceOf(InvalidTransitionError);
    expect(caught).toBeInstanceOf(Error);
    expect(caught.from).toBe("idle");
    expect(caught.event).toBe("ok");
    expect(m.status).toBe("idle", {
        message: "a refused transition must not move the machine",
    });
});

test("an unknown source state throws rather than silently going undefined", () => {
    const m = new ProbeMachine();
    m.status = "nowhere";
    let caught;
    try {
        m._transition("begin");
    } catch (error) {
        caught = error;
    }
    expect(caught).toBeInstanceOf(InvalidProbeTransitionError);
    expect(caught.from).toBe("nowhere", {
        message: "the error names the state it was actually in, not a known one",
    });
    expect(m.status).toBe("nowhere");
});

test("the error carries name, message, from and event", () => {
    const err = new InvalidProbeTransitionError("idle", "ok");
    expect(err.name).toBe("InvalidProbeTransitionError");
    expect(err.message).toBe("ProbeMachine: invalid transition 'ok' from state 'idle'");
    expect(err.from).toBe("idle");
    expect(err.event).toBe("ok");
});

test("the status is reactive, as SignalStore promises", () => {
    const m = new ProbeMachine();
    const steps = [];
    const { reactive } = /** @type {any} */ (odoo.loader.modules.get("@odoo/owl"));
    const tracked = reactive(m, () => steps.push(tracked.status));
    void tracked.status;
    tracked._transition("begin");
    expect(steps.length).toBeGreaterThan(0, {
        message: "a transition must notify subscribers of `status`",
    });
});
