import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { ProfileDialog } from "../components/profile_dialog/profile_dialog";

export class ProfileEditor extends Interaction {
    static selector = ".o_wprofile_editor";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": this.openDialog,
        },
    };

    openDialog() {
        this.services.dialog.add(ProfileDialog, {
            confirm: () => {
                const url = new URL(window.location.href);
                if (this.el.dataset.urlFrom && !url.searchParams.has("url_from")) {
                    url.searchParams.set("url_from", this.el.dataset.urlFrom);
                    window.location.replace(url.toString());
                } else {
                    browser.location.reload();
                }
            },
            focusWebsiteDescription:
                this.el.dataset.focusWebsiteDescription &&
                this.el.dataset.focusWebsiteDescription === "true",
            userId: parseInt(this.el.dataset.userId),
        });
    }
}

registry
    .category("public.interactions")
    .add("website_profile.profile_editor", ProfileEditor);
