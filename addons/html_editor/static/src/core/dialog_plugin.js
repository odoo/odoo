import { Plugin } from "../plugin";

export class DialogPlugin extends Plugin {
    static name = "dialog";
    static dependencies = ["selection"];
    static shared = ["addDialog"];

    addDialog(dialogClass, props, options = {}) {
        this.services.dialog.add(dialogClass, props, {
            onClose: () => {
                this.shared.focusEditable();
            },
            ...options,
        });
    }
}
