import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";

export class LinkTrackerDialogFormController extends FormController {
    static props = {
        ...FormController.props,
    };
}

registry.category("views").add("link_tracker_dialog_form", {
    ...formView,
    Controller: LinkTrackerDialogFormController,
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
        this.website = useService("website");
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
        if (this.props.resModel) {
            return this.props.resModel;
        }
        return "link.tracker.dialog";
    }
}
