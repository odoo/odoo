import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { renderToMarkup } from "@web/core/utils/render";
import { InputConfirmationDialog } from '../js/components/input_confirmation_dialog/input_confirmation_dialog';

import { handleCheckIdentity } from './tools';

export class NewAPIKey extends Interaction {
    static selector = ".o_portal_new_api_key";
    dynamicContent = {
        _root: { "t-on-click.prevent": this.onClick },
    };

    async onClick() {
        // This call is done just so it asks for the password confirmation before starting displaying the
        // dialog forms, to mimic the behavior from the backend, in which it asks for the password before
        // displaying the wizard.
        // The result of the call is unused. But it's required to call a method with the decorator `@check_identity`
        // in order to use `handleCheckIdentity`.
        await this.waitFor(handleCheckIdentity(
            this.services.orm.call("res.users", "api_key_wizard", [user.userId]),
            this.services.orm,
            this.services.dialog,
        ));

        this.services.dialog.add(InputConfirmationDialog, {
            title: _t("New API Key"),
            body: renderToMarkup("portal.keydescription"),
            confirmLabel: _t("Confirm"),
            confirm: async ({ inputEl }) => {
                const description = inputEl.value;
                const wizard_id = await this.waitFor(this.services.orm.create("res.users.apikeys.description", [{ name: description }]));
                const res = await this.waitFor(handleCheckIdentity(
                    this.services.orm.call("res.users.apikeys.description", "make_key", [wizard_id]),
                    this.services.orm,
                    this.services.dialog,
                ));
                this.services.dialog.add(ConfirmationDialog, {
                    title: _t("API Key Ready"),
                    body: renderToMarkup("portal.keyshow", { key: res.context.default_key }),
                    confirmLabel: _t("Close"),
                }, {
                    onClose: () => { window.location = window.location },
                })
            }
        });
    }
}

registry
    .category("public.interactions")
    .add("portal.new_api_key", NewAPIKey);

