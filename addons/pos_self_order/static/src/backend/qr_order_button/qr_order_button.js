import { registry } from "@web/core/registry";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { _t } from "@web/core/l10n/translation";

async function posQrStands(env, action) {
    const user_data = action.params.data;

    function addInputToForm(form, name, value) {
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = name;
        input.value = value;
        form.appendChild(input);
    }

    if (user_data && user_data.success && user_data.redirect_url) {
        // Temporary form to avoid URL length issues
        const form = document.createElement("form");
        form.method = "POST";
        form.target = "_blank";
        form.action = user_data.redirect_url;
        form.style.display = "none";

        addInputToForm(form, "db_name", user_data.db_name);
        addInputToForm(form, "table_data", JSON.stringify(user_data.table_data));
        addInputToForm(form, "self_ordering_mode", user_data.self_ordering_mode);
        addInputToForm(form, "zip_archive", user_data.zip_archive);

        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    } else {
        env.services.dialog.add(WarningDialog, {
            title: _t("Get QR codes"),
            message: _t(
                "Enable QR menu in the Restaurant settings to get QR codes for free on tables."
            ),
        });
    }
    return action.params.next;
}

registry.category("actions").add("pos_qr_stands", posQrStands);
