import { Image } from "@html_builder/core/img";
import { Component, proxy, signal, useProps, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useAutofocus } from "@web/core/utils/hooks";

export class CustomInnerSnippet extends Component {
    static template = "html_builder.CustomInnerSnippet";
    props = useProps({
        snippetModel: t.object(),
        snippet: t.object(),
        onClickHandler: t.function(),
        disabledTooltip: t.string(),
    });
    static components = { Image };

    renameInputRef = signal.ref();

    setup() {
        useAutofocus({ ref: this.renameInputRef });

        this.state = proxy({ isRenaming: false });

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
        this.props.snippetModel.renameCustomSnippet(this.snippet, this.renameInputRef().value);
        this.toggleRenamingState();
    }
}
