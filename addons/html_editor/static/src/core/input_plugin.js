import { Plugin } from "../plugin";

export class InputPlugin extends Plugin {
    static name = "input";
    setup() {
        this.addDomListener(this.editable, "beforeinput", this.onBeforeInput);
        this.addDomListener(this.editable, "input", this.onInput);
    }

    onBeforeInput(ev) {
        this.dispatch("HISTORY_STAGE_SELECTION");
        for (const handler of this.getResource("onBeforeInput")) {
            handler(ev);
        }
    }

    onInput(ev) {
        this.dispatch("ADD_STEP");
        for (const handler of this.getResource("onInput")) {
            handler(ev);
        }
    }
}
