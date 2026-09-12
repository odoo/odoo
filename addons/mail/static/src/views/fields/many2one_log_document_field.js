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
            // Opening the document changes nothing to the wizard: saving and reloading
            // it, as a many2one does, would only lose the type of document it logs on,
            // which lives in the form alone.
            willOpenRecordInDialog: () => true,
            onRecordSaved: () => {},
        };
    }
}

registry.category("fields").add("many2one_log_document", {
    ...buildM2OFieldDescription(Many2OneLogDocumentField),
    displayName: _t("Many2one of a Logged Document"),
});
