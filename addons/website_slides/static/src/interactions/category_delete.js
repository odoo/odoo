import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class CategoryDelete extends Interaction {
    static selector = ".o_wslides_js_category_delete";
    dynamicContent = {
        _root: {
            "t-on-click": this.openDialog,
        },
    };

    openDialog() {
        const categoryId = parseInt(this.el.dataset.categoryId);
        this.services.dialog.add(ConfirmationDialog, {
            title: _t("Delete Category"),
            body: _t("Are you sure you want to delete this category?"),
            confirmLabel: _t("Delete"),
            confirm: async () => {
                /**
                 * Calls 'unlink' method on slides.slide to delete the category and
                 * reloads page after deletion to re-arrange the content on UI
                 */
                await this.waitFor(this.services.orm.unlink("slide.slide", [categoryId]));
                window.location.reload();
            },
            cancelLabel: _t("Cancel"),
            cancel: () => { },
        });
    }
}

registry
    .category("public.interactions")
    .add("website_slides.category_delete", CategoryDelete);
