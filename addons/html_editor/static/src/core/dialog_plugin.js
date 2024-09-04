import { Plugin } from "../plugin";

export class DialogPlugin extends Plugin {
    static name = "dialog";
    static dependencies = ["selection"];
    static shared = ["addDialog"];

    addDialog(dialogClass, props, options = {}) {
        return new Promise((resolve) => {
            this.services.dialog.add(dialogClass, props, {
                onClose: () => {
                    this.shared.focusEditable();
                    resolve();
                },
                ...options,
            });
        });
    }
}
