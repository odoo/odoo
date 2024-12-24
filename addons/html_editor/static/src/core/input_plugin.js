import { Plugin } from "../plugin";

export class InputPlugin extends Plugin {
    static id = "input";
    static dependencies = ["history"];
    setup() {
        this.addDomListener(this.editable, "beforeinput", this.onBeforeInput);
        this.addDomListener(this.editable, "input", this.onInput);
    }

    onBeforeInput(ev) {
        this.dependencies.history.stageSelection();
        this.dispatchTo("beforeinput_handlers", ev);
    }

    onInput(ev) {
        this.dependencies.history.addStep();
        this.dispatchTo("input_handlers", ev);
    }
}
