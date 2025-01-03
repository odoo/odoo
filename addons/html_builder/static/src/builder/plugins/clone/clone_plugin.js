import { Plugin } from "@html_editor/plugin";

export class ClonePlugin extends Plugin {
    static id = "clone";
    static dependencies = ["history"];
    static shared = ["cloneElement"];

    // TODO find why the images should not have the clone buttons.
    setup() {}

    cloneElement(el) {
        // TODO snippet_will_be_cloned ?
        // TODO cleanUI resource for each option
        const cloneEl = el.cloneNode(true);
        el.insertAdjacentElement("afterEnd", cloneEl);
        this.dispatchTo("update_containers", cloneEl);
        // TODO onClone resource for each option
        // TODO snippet_cloned ?
        this.dependencies.history.addStep();
    }
}
