import { Img } from "@html_builder/core/img";
import { Component } from "@odoo/owl";

export class Snippet extends Component {
    static template = "html_builder.Snippet";
    static components = { Img };
    static props = {
        snippetModel: { type: Object },
        snippet: { type: Object },
        onClickHandler: { type: Function },
        disabledTooltip: { type: String },
    };

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
