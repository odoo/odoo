import { t, useProps } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { FormController } from "@web/views/form/form_controller";
import { formView } from "@web/views/form/form_view";
import { formViewDialogProps, FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export class LinkTrackerFormController extends FormController {
    manageTrackedLinks() {
        return this.actionService.doAction("website_links.action_link_tracker_tree");
    }
}

// Register the form view for the link tracker dialog
registry.category("views").add("link_tracker_dialog_form", {
    ...formView,
    Controller: LinkTrackerFormController,
});

export const websiteLinksFormViewDialogProps = {
    ...formViewDialogProps,
    title: t.string().optional(_t("Create Tracked Link")),
    size: t.string().optional("md"),
    onClose: t.function().optional(),
};

export class LinkTrackerDialog extends FormViewDialog {
    props = useProps(websiteLinksFormViewDialogProps);

    setup() {
        super.setup();
        this.viewProps = {
            ...this.viewProps,
            context: {
                ...this.viewProps.context,
                form_view_ref: "website_links.website_link_tracker_view_form",
                default_url: browser.location.href,
            },
            buttonDialogTemplate: "website_links.LinkTrackerDialogButtons",
        };
    }
}
