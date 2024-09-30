import { trigger } from "@html_editor/utils/resource";
import { Plugin } from "../plugin";

export class InputPlugin extends Plugin {
    static name = "input";
    static dependencies = ["history"];
    setup() {
        this.addDomListener(this.editable, "beforeinput", this.onBeforeInput);
        this.addDomListener(this.editable, "input", this.onInput);
    }

    onBeforeInput(ev) {
        this.shared.stageSelection();
        trigger(this.getResource("onBeforeInput"), ev);
    }

    onInput(ev) {
        this.shared.addStep();
        trigger(this.getResource("onInput"), ev);
    }
}
