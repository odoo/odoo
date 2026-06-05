import { Component, proxy, signal } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";

export class AnchorDialog extends Component {
    static template = "html_builder.AnchorDialog";
    static components = { Dialog };
    static props = {
        currentAnchorName: { type: String },
        renameAnchor: { type: Function },
        deleteAnchor: { type: Function },
        formatAnchor: { type: Function },
        close: { type: Function },
    };

    inputRef = signal(null);

    setup() {
        this.title = _t("Link Anchor");
        this.state = proxy({ isValid: true });
    }

    async onConfirmClick() {
        const newAnchorName = this.props.formatAnchor(this.inputRef()?.value);
        if (newAnchorName === this.props.currentAnchorName) {
            this.props.close();
        }

        this.state.isValid = await this.props.renameAnchor(newAnchorName);
        if (this.state.isValid) {
            this.props.close();
        }
    }

    onRemoveClick() {
        this.props.deleteAnchor();
        this.props.close();
    }
}
