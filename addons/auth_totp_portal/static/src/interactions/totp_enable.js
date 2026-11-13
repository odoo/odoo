import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { TotpConfirmationDialog } from "../components/totp_confirmation_dialog";
import { handleCheckIdentity } from "@portal/interactions/portal_security";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { renderToMarkup } from "@web/core/utils/render";

export class TOTPEnable extends Interaction {
    static selector = "#auth_totp_portal_enable";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.onClick },
    };

    async onClick() {
        const data = await this.waitFor(handleCheckIdentity(
            this.waitFor(this.services.orm.call("res.users", "action_totp_enable_wizard", [user.userId])),
            this.services.orm,
            this.services.dialog,
        ));

        if (!data) {
            // TOTP probably already enabled, just reload page
            location.reload()
            return;
        }

        const model = data.res_model;
        const wizard_id = data.res_id;
        const [record] = await this.services.orm.read(model, [wizard_id], ["secret", "qrcode"]);

        this.services.dialog.add(TotpConfirmationDialog, {
            title: _t("Enable two-factor authentication"),
            body: renderToMarkup("auth_totp_portal.totp_setup", {
                secret: record.secret,
                qrcode_src: `data:image/png;base64,${record.qrcode.content}`,
            }),
            onInput: ({ inputEl }) => {
                inputEl.classList.remove("is-invalid");
                inputEl.setCustomValidity("");
            },
            confirmLabel: _t("Activate"),
            size: "md",
            confirm: async ({ inputEl }) => {
                if (!inputEl.reportValidity()) {
                    inputEl.classList.add("is-invalid");
                    return false;
                }

                try {
                    await handleCheckIdentity(
                        this.waitFor(this.services.orm.call(model, "enable",
                            [ record.id ],
                            { 'context': {'code': inputEl.value} },
                        )),
                        this.services.orm,
                        this.services.dialog
                    );
                } catch (e) {
                    const errorMessage = (
                        !e.message ? e.toString()
                            : !e.message.data ? e.message.message || _t("Verification failed, please double-check the 6-digit code")
                                : e.message.data.message || _t("Operation failed for unknown reason.")
                    );
                    inputEl.classList.add("is-invalid");
                    // show custom validity error message
                    inputEl.setCustomValidity(errorMessage);
                    inputEl.reportValidity();
                    return false;
                }
                // reloads page, avoid window.location.reload() because it re-posts forms
                location.reload();
            },
            cancel: () => { },
        });
    }
}

registry
    .category("public.interactions")
    .add("auth_totp_portal.totp_enable", TOTPEnable);
