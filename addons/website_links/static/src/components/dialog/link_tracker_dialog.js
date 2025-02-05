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
        onClose: { type: Function, optional: true },
        resModel: { type: String, optional: true },
    };

    static defaultProps = {
        ...FormViewDialog.defaultProps,
        title: _t("Create Tracked Link"),
        size: "md",
        onClose: () => {},
    };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.website = useService("website");

        this.viewProps = {
            ...this.viewProps,
            resId: this.resId,
            resModel: this.resModel,
            context: Object.assign(
                {
                    form_view_ref: "website_links.link_tracker_view_form",
                },
                this.viewProps.context
            ),
            ...{},
        };
    }

    get resId() {
        return this.props.resId;
    }

    get resModel() {
        if (this.props.resModel) {
            return this.props.resModel;
        }
        return "link.tracker.dialog";
    }

    get targetId() {
        return this.website.currentWebsite?.metadata.mainObject.id;
    }

    get targetModel() {
        return this.website.currentWebsite?.metadata.mainObject.model;
    }

    get isPage() {
        return this.targetModel === "website.page";
    }
}
