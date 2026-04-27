import { makeKwArgs, onRpc } from "@web/../tests/web_test_helpers";

onRpc("web_gantt_write", function webGanttWrite({ args, kwargs, model }) {
    return this.env[model].write(...args, makeKwArgs({ context: kwargs.context }));
});
