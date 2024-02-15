import { Persona } from "@mail/core/common/persona_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Persona.prototype, {
    get nameOrDisplayName() {
        if (this.type === "visitor" && !this.name) {
            return _t("Visitor #%s", this.id);
        }
        return super.nameOrDisplayName;
    },
});
