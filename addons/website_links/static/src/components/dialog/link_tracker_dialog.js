import { _t } from "@web/core/l10n/translation";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";

registry.category("views").add("link_tracker_dialog_form", {
    ...formView,
});

export class LinkTrackerDialog extends FormViewDialog {
    static props = {
        ...FormViewDialog.props,
    };

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
            resModel: this.resModel,
            context: Object.assign(
                {
                    form_view_ref: "website_links.link_tracker_view_form",
                },
                this.viewProps.context
            ),
            ...{ buttonTemplate: "website_link.LinkTrackerDialogButtons" },
        };
    }
    get resModel() {
        return this.props.resModel;
    }
}
