import { formView } from "@web/views/form/form_view";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

// Register the form view for the link tracker dialog
registry.category("views").add("link_tracker_dialog_form", {
    ...formView,
});

export class LinkTrackerDialog extends FormViewDialog {
    static defaultProps = {
        ...FormViewDialog.defaultProps,
        title: _t("Create Tracked Link"),
        size: "md",
        onClose: () => {},
    };

    setup() {
        super.setup();
        this.viewProps = {
            ...this.viewProps,
            context: {
                ...this.viewProps.context,
                form_view_ref: "website_links.website_link_tracker_view_form",
                default_url: document.location.href,
            },
            buttonTemplate: "website_link.LinkTrackerDialogButtons",
        };
    }
}
