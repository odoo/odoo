import { loadEditorBundle } from "@html_editor/public/load_editor_bundle";
import { location } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class ProfileEditor extends Interaction {
    static selector = ".o_wprofile_editor";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": this.openDialog,
        },
    };

    async openDialog() {
        await this.waitFor(loadEditorBundle("website_profile.assets_html_editor"));
        const ProfileDialog = registry
            .category("lazy_components")
            .get("website_profile.ProfileDialog");
        this.services.dialog.add(ProfileDialog, {
            confirm: () => {
                location.reload();
            },
            focusWebsiteDescription:
                this.el.dataset.focusWebsiteDescription &&
                this.el.dataset.focusWebsiteDescription === "true",
            userId: parseInt(this.el.dataset.userId),
            canEditCountry: this.el.dataset.canEditCountry === "true",
        });
    }
}

registry.category("public.interactions").add("website_profile.profile_editor", ProfileEditor);
