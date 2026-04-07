import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

const VIEW_IN_BROWSER_LINK_SELECTOR = "o_snippet_view_in_browser";

export class ViewInBrowserOptionPlugin extends Plugin {
    static id = "mass_mailing.ViewInBrowserOptionPlugin";
    static shared = ["isPresent", "insertViewInBrowserLink", "removeViewInBrowserLink"];
    static dependencies = ["history"];

    resources = {
        builder_actions: {
            ToggleViewInBrowserAction,
        },
    };

    isPresent() {
        return !!this.linkElement;
    }

    insertViewInBrowserLink() {
        if (this.isPresent()) {
            return;
        }

        const linkElement = this._buildViewInBrowserLinkElement();
        this.editable.querySelector(".o_mail_wrapper .o_mail_wrapper_td").prepend(linkElement);
        this.dependencies.history.addStep();
    }

    removeViewInBrowserLink() {
        if (!this.isPresent()) {
            return;
        }
        this.linkElement.remove();
        this.dependencies.history.addStep();
    }

    get linkElement() {
        return this.editable.querySelector(`.${VIEW_IN_BROWSER_LINK_SELECTOR}`);
    }

    _buildViewInBrowserLinkElement() {
        const section = this.document.createElement("section");
        section.classList.add(
            VIEW_IN_BROWSER_LINK_SELECTOR,
            "o_mail_snippet_general",
            "pt16",
            "pb16"
        );
        section.dataset.name = "View Online";
        section.dataset.vxml = "001";
        section.innerHTML = `
            <p style="text-align: center" class="mb-0">
                <a href="/view">View in Browser</a>
            </p>
        `;

        return section;
    }
}

export class ToggleViewInBrowserAction extends BuilderAction {
    static id = "mass_mailing.ToggleViewInBrowserAction";
    static dependencies = ["mass_mailing.ViewInBrowserOptionPlugin"];

    setup() {
        this.preview = false;
    }

    apply() {
        if (!this.isApplied(...arguments)) {
            this.dependencies["mass_mailing.ViewInBrowserOptionPlugin"].insertViewInBrowserLink();
        } else {
            this.dependencies["mass_mailing.ViewInBrowserOptionPlugin"].removeViewInBrowserLink();
        }
    }

    isApplied() {
        console.log();
        return this.dependencies["mass_mailing.ViewInBrowserOptionPlugin"].isPresent();
    }
}

registry
    .category("mass_mailing-plugins")
    .add(ViewInBrowserOptionPlugin.id, ViewInBrowserOptionPlugin);
