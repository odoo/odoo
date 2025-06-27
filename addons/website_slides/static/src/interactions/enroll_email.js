import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { createElementWithContent } from "@web/core/utils/html";

export class EnrollEmail extends Interaction {
    static selector = "#wrapwrap";
    dynamicContent = {
        ".o_wslides_js_channel_enroll": {
            "t-on-click.prevent.withTarget": this.openDialog,
        },
    };

    /**
     * @param {MouseEvent} ev
     * @param {HTMLElement} currentTargetEl
     */
    openDialog(ev, currentTargetEl) {
        const alertEl = currentTargetEl.closest(".alert");
        const channelId = parseInt(currentTargetEl.dataset.channelId);
        this.services.dialog.add(ConfirmationDialog, {
            title: _t("Request Access."),
            body: _t("Do you want to request access to this course?"),
            confirmLabel: _t("Yes"),
            confirm: async () => {
                const { error, done } = await this.waitFor(
                    this.services.orm.call(
                        "slide.channel",
                        "action_request_access",
                        [channelId],
                    )
                );
                const message = done ? _t("Request sent!") : error || _t("Unknown error, try again.");

                const newAlertEl = document.createElement("div");
                newAlertEl.classList.add("alert", done ? "alert-success" : "alert-danger");
                newAlertEl.role = "alert";
                newAlertEl.appendChild(createElementWithContent("strong", message));
                this.insert(newAlertEl, alertEl, "afterend");
                alertEl.remove();
            },
            cancelLabel: _t("Cancel"),
            cancel: () => { },
        });
    }
}

registry
    .category("public.interactions")
    .add("website_slides.enroll_email", EnrollEmail);
