import { Dialog } from "@web/core/dialog/dialog";
import { CodeEditor } from "@web/core/code_editor/code_editor";
import { useService } from "@web/core/utils/hooks";
import { EditHeadBodyDialog } from "@website/components/edit_head_body_dialog/edit_head_body_dialog";
import { Component, useState } from "@odoo/owl";

export class EmbedCodeOptionDialog extends Component {
    static template = "website.EmbedCodeOptionDialog";
    static components = { Dialog, CodeEditor };
    static props = {
        title: String,
        value: String,
        mode: String,
        confirm: Function,
        close: Function,
    };
    setup() {
        this.dialog = useService("dialog");
        this.state = useState({ value: this.props.value });
    }
    onCodeChange(newValue) {
        this.state.value = newValue;
    }
    onConfirm() {
        this.props.confirm(this.state.value);
        this.props.close();
    }
    onInjectHeadOrBody() {
        this.dialog.add(EditHeadBodyDialog);
        this.props.close();
    }
}
