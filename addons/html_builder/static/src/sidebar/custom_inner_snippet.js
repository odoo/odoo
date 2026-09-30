import { Img } from "@html_builder/core/img";
import { Component, useState, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useAutofocus } from "@web/core/utils/hooks";

export class CustomInnerSnippet extends Component {
    static template = "html_builder.CustomInnerSnippet";
    static props = {
        snippetModel: { type: Object },
        snippet: { type: Object },
        onClickHandler: { type: Function },
        disabledTooltip: { type: String },
    };
    static components = { Img };

    setup() {
        this.renameInputRef = useRef("rename-input");
        useAutofocus({ refName: "rename-input" });

        this.state = useState({ isRenaming: false });

        this.renameButtonTooltip = _t("Rename %(snippetTitle)s", {
            snippetTitle: this.snippet.title,
        });
        this.deleteButtonTooltip = _t("Delete %(snippetTitle)s", {
            snippetTitle: this.snippet.title,
        });
    }

    get snippet() {
        return this.props.snippet;
    }

    toggleRenamingState() {
        this.state.isRenaming = !this.state.isRenaming;
    }

    onConfirmRename() {
        this.props.snippetModel.renameCustomSnippet(this.snippet, this.renameInputRef.el.value);
        this.toggleRenamingState();
    }
}
