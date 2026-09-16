import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

/**
 * The document a call is logged on, in the "Log Activity in Chatter" wizard.
 */
export class Many2OneLogDocumentField extends Many2OneField {
    get m2oProps() {
        return {
            ...super.m2oProps,
            // The wizard holds the type of document it logs on in the form alone, so
            // the reload a many2one runs after opening a record would wipe it. Open the
            // document in a dialog and skip that reload.
            willOpenRecordInDialog: () => true,
            onRecordSaved: () => {},
        };
    }
}

registry.category("fields").add("many2one_log_document", {
    ...buildM2OFieldDescription(Many2OneLogDocumentField),
    displayName: _t("Many2one of a Logged Document"),
});
