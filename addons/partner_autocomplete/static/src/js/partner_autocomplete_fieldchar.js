/** @odoo-module native */
import { useChildRef, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/fields/basic/char/char_field";
import { useInputField } from "@web/fields/input_field_hook";

import { usePartnerAutocomplete } from "@partner_autocomplete/js/partner_autocomplete_core";
import { PartnerAutoComplete } from "@partner_autocomplete/js/partner_autocomplete_component";

export class PartnerAutoCompleteCharField extends CharField {
    static template = "partner_autocomplete.PartnerAutoCompleteCharField";
    static components = {
        ...CharField.components,
        PartnerAutoComplete,
    };
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.partnerAutocomplete = usePartnerAutocomplete();

        this.inputRef = useChildRef();
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            parse: (v) => this.parse(v),
            ref: this.inputRef,
        });
    }

    get sources() {
        return [
            this.partnerAutocomplete.makeAutocompleteSource({
                cssClass: "partner_autocomplete_dropdown_char",
                getCountryId: () => this.props.record.data?.country_id?.id || false,
                onSelectOption: (suggestion) =>
                    this.onSelectPartnerAutocompleteOption(suggestion),
            }),
        ];
    }

    async onSelectPartnerAutocompleteOption(option) {
        let data = await this.partnerAutocomplete.getCreateData(option);
        if (!data?.company) {
            return;
        }

        if (data.logo) {
            // `data.logo` is a URL (e.g. https://logo.clearbit.com/...), not
            // base64 image bytes. Writing it under the target field's own
            // name here means the server will reject it loudly if the
            // record is ever saved with no further processing in between.
            data.company.image_1920 = data.logo;
        }

        const additionalData = {
            entity_type: data.company.entity_type,
            unspsc_codes: data.company.unspsc_codes,
        };
        data.company = this.partnerAutocomplete.removeUselessFields(
            data.company,
            Object.keys(this.props.record.fields),
        );

        // Update record with retrieved values.
        // The widget lives on the `name` input, which is `isDirty` from the typed
        // query. useInputField only resyncs the DOM input from the record while
        // NOT dirty, so writing the enriched name in the bulk update below can be
        // overwritten by the stale typed value on the next commit. Writing name on
        // its own first settles it before the rest of the payload lands.
        if (data.company.name) {
            await this.props.record.update({ name: data.company.name });
        }
        await this.props.record.update(data.company);

        // Post message with company info card
        if (this.props.record.resModel === "res.partner") {
            const saved = await this.props.record.save();
            if (saved && data.isEnrichAccessible) {
                await this.orm.call("res.partner", "enrich_company_message_post", [
                    this.props.record.resId,
                    additionalData,
                ]);
                this.props.record.load();
            }
        }
        if (this.props.setDirty) {
            this.props.setDirty(false);
        }
    }
}

export const partnerAutoCompleteCharField = {
    ...charField,
    component: PartnerAutoCompleteCharField,
};

registry
    .category("fields")
    .add("field_partner_autocomplete", partnerAutoCompleteCharField);
