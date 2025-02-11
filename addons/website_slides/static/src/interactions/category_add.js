import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { CategoryAddDialog } from "@website_slides/js/public/components/category_add_dialog/category_add_dialog";

export class CategoryAdd extends Interaction {
    static selector = ".o_wslides_js_slide_section_add";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": this.openDialog,
        },
    };

    openDialog() {
        const channelId = this.el.getAttribute("channel_id");
        this.services.dialog.add(CategoryAddDialog, {
            title: _t("Add a section"),
            confirmLabel: _t("Save"),
            confirm: ({ formEl }) => {
                if (!formEl.checkValidity()) {
                    return false;
                }
                formEl.classList.add("was-validated");
                formEl.submit();
                return true;
            },
            cancelLabel: _t("Cancel"),
            cancel: () => { },
            channelId,
        });
    }
}

registry
    .category("public.interactions")
    .add("website_slides.category_add", CategoryAdd);
