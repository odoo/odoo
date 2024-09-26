import { trigger } from "@html_editor/utils/resource";
import { Plugin } from "../plugin";

export class InputPlugin extends Plugin {
    static name = "input";
    setup() {
        this.addDomListener(this.editable, "beforeinput", this.onBeforeInput);
        this.addDomListener(this.editable, "input", this.onInput);
    }

    onBeforeInput(ev) {
        this.dispatch("HISTORY_STAGE_SELECTION");
        trigger(this.getResource("onBeforeInput"), ev);
    }

    onInput(ev) {
        this.dispatch("ADD_STEP");
        trigger(this.getResource("onInput"), ev);
    }
}
