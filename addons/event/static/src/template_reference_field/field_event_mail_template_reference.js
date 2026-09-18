import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";
import { ReferenceField, referenceField } from "@web/views/fields/reference/reference_field";

export class EventMailTemplateReferenceField extends ReferenceField {
    static template = "event.mailTemplateReferenceField";

    setup() {
        const returnVal = super.setup();
        // select the first value by default
        // selection is [['mail', 'Mail Template'], ['sms', 'Sms Template'], ...]
        const defaultSelect = this.selection?.[0][0];
        if (defaultSelect) {
            this.state.currentRelation = defaultSelect;
        }
        return returnVal;
    }

    /**
     * Make not openable in readonly mode
     * as we expect m2o fields to just be strings in list view
     */
    get m2oProps() {
        const props = super.m2oProps;
        if (props.readonly) {
            props.canOpen = false;
        }
        if (props.context.filter_template_on_event) {
            let currentDomain = props.domain || [];
            if (typeof currentDomain === "function") {
                currentDomain = currentDomain();
            }
            const baseDomain = new Domain(currentDomain);
            const excludeDomain = new Domain([
                ["model", "=", "event.registration"],
            ]);
            props.domain = () => Domain.and([baseDomain, excludeDomain]).toList();
        }
        return props;
    }
}

export const eventMailTemplateReferenceField = {
    ...referenceField,
    component: EventMailTemplateReferenceField,
    displayName: _t("Event Mail Template Reference"),
};

registry.category("fields").add("EventMailTemplateReferenceField", eventMailTemplateReferenceField);
