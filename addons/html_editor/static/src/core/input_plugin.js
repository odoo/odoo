import { Plugin } from "../plugin";

export class InputPlugin extends Plugin {
    static name = "input";
    setup() {
        const sequence = (resource) => resource.sequence ?? 50;
        this.resources.onBeforeInput?.sort((a, b) => sequence(a) - sequence(b));
        this.resources.onInput?.sort((a, b) => sequence(a) - sequence(b));

        this.addDomListener(this.editable, "beforeinput", this.onBeforeInput);
        this.addDomListener(this.editable, "input", this.onInput);
    }

    onBeforeInput(ev) {
        this.dispatch("HISTORY_STAGE_SELECTION");
        for (const { handler } of this.resources.onBeforeInput || []) {
            handler(ev);
        }
    }

    onInput(ev) {
        this.dispatch("ADD_STEP");
        for (const { handler } of this.resources.onInput || []) {
            handler(ev);
        }
    }
}
