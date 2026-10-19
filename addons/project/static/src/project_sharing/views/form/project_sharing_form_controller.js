import { _t } from "@web/core/l10n/translation";
import { FormController } from "@web/views/form/form_controller";
import { useService } from "@web/core/utils/hooks";
import { useListener } from "@odoo/owl";

export class ProjectSharingFormController extends FormController {
    static components = {
        ...FormController.components,
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
        useListener(window, "paste", this.onGlobalPaste.bind(this), { capture: true });
        useListener(window, "drop", this.onGlobalDrop.bind(this), { capture: true });
    }

    onWillLoadRoot(nextConfiguration) {
        super.onWillLoadRoot(...arguments);
        const isSameThread =
            this.model.root?.resId === nextConfiguration.resId &&
            this.model.root?.resModel === nextConfiguration.resModel;
        if (isSameThread) {
            const { resModel, resId } = this.model.root;
            this.env.bus.trigger("MAIL:RELOAD-THREAD", { model: resModel, id: resId });
        }
    }

    get actionMenuItems() {
        return {};
    }

    get translateAlert() {
        return null;
    }

    onGlobalPaste(ev) {
        if (ev.target.closest('.o_field_widget[name="description"]')) {
            ev.preventDefault();
            const items = ev.clipboardData.items;
            for (let i = 0; i < items.length; i++) {
                if (items[i].type.indexOf("image") !== -1 && !this.model.root.resId) {
                    this.notification.add(
                        _t("Save the task to be able to paste images in description"),
                        { type: "warning" }
                    );
                    ev.stopImmediatePropagation();
                    return;
                }
            }
        }
    }

    onGlobalDrop(ev) {
        if (ev.target.closest('.o_field_widget[name="description"]')) {
            ev.preventDefault();
            if (ev.dataTransfer.files.length > 0 && !this.model.root.resId) {
                this.notification.add(
                    _t("Save the task to be able to drag images in description"),
                    { type: "warning" }
                );
                ev.stopImmediatePropagation();
            }
        }
    }
}
