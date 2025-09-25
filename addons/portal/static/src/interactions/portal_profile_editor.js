import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { PortalProfileDialog } from "../js/components/portal_profile_dialog/portal_profile_dialog";

export class PortalProfileEditor extends Interaction {
    static selector = ".o_portal_profile_editor";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": this.openDialog,
        },
    };

    openDialog() {
        this.services.dialog.add(PortalProfileDialog, {
            confirm: () => {
                browser.location.reload();
            },
            userId: parseInt(this.el.dataset.userId),
        });
    }
}

registry.category("public.interactions").add("portal.portal_profile_editor", PortalProfileEditor);
