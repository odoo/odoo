import { Component, onMounted, signal, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class RenameDialog extends Component {
    static template = "html_editor.RenameDialog";
    static components = {
        Dialog: Dialog,
    };

    props = useProps({
        filename: t.string(),
        rename: t.function(),
        close: t.function(),
    });
    nameInputRef = signal.ref();

    setup() {
        onMounted(() => {
            const nameInput = this.nameInputRef();
            nameInput?.focus();
            nameInput?.select();
        });
    }

    onKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.rename();
        }
    }

    rename() {
        const name = this.nameInputRef().value;
        this.props.rename(name);
        this.props.close();
    }
}
