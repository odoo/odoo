import { Image } from "@html_builder/core/img";
import { Component, useProps, t } from "@odoo/owl";

export class Snippet extends Component {
    static template = "html_builder.Snippet";
    static components = { Image };
    props = useProps({
        snippetModel: t.object(),
        snippet: t.object(),
        onClickHandler: t.function(),
        onSnippetKeydown: t.function(),
        disabledTooltip: t.string(),
    });

    get snippet() {
        return this.props.snippet;
    }

    onInstallableHover(ev) {
        if (this.snippet.isInstallable) {
            ev.currentTarget
                .querySelector(".o_install_btn")
                .classList.toggle("visually-hidden-focusable", ev.type !== "mouseover");
        }
    }

    onClickInstall() {
        this.props.snippetModel.installSnippetModule(
            this.props.snippet,
            this.env.editor.config.installSnippetModule
        );
    }
}
