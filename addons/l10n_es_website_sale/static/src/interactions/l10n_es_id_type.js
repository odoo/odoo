import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class L10nEsIdType extends Interaction {
    // The select and its value input are plain sibling columns (no wrapper div, so they keep the
    // form's regular Bootstrap column gutter) -- reach the input/label via the native `form`
    // reference instead of a shared ancestor.
    static selector = "#l10n_es_id_type_select";
    dynamicContent = {
        _root: { "t-on-change": this.onChangeIdType },
    };

    /**
     * Rename the value input to the newly selected ID-type key, so the submitted field lands on
     * the right `additional_identifiers` entry, and update its label to match.
     *
     * @param {Event} ev
     */
    onChangeIdType(ev) {
        const select = ev.currentTarget;
        const form = select.form;
        if (!form) return;
        const input = form.querySelector("#l10n_es_id_value_input");
        const label = form.querySelector("#l10n_es_id_value_label");
        if (input) {
            input.name = select.value;
        }
        if (label) {
            label.textContent = select.selectedOptions[0]?.textContent ?? "";
        }
    }
}

registry.category("public.interactions").add("l10n_es_website_sale.id_type", L10nEsIdType);
