import { Component, useEffect, useState } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    m2oSupportedOptions,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";

export class MailingFilterDropdown extends Dropdown {
    setup() {
        super.setup();
        useEffect(
            (inputFilterEl) => {
                if (inputFilterEl) {
                    inputFilterEl.focus();
                }
            },
            () => [document.querySelector(".o_mass_mailing_filter_name")]
        );
    }
}

/**
 * Widget to create / remove favorite filters on mass mailing and/or marketing automation, extended
 * from Many2OneField. This widget is designed specifically for 'mailing_filter_id'
 * field on 'mailing.mailing' and 'marketing.campaign' form view.
 *
 * In edit mode, it will allow to save the latest configured domain
 * in form of the favorite filter, or to remove the store filters.
 *
 */
export class Many2OneMailingFilter extends Many2One {
    static template = "mass_mailing.Many2OneMailingFilter";
    static components = {
        ...super.components,
        MailingFilterDropdown,
    };
    static props = {
        ...super.props,
        mailingDomain: { type: String, optional: true },
        mailingFilterCount: Number,
        mailingFilterDomain: String,
        mailingFilterId: [Number, { value: false }],
        modelField: { type: String, optional: true },
        updateMailingDomain: Function,
    };

    setup() {
        super.setup();
        this.notification = useService("notification");
        this.filter = useState({
            canSaveFilter: false,
            canRemoveFilter: false,
        });
        useEffect(() => this._updateFilterIcons());
    }

    /**
     * Updates the 'Add to favorite' / 'Remove' icons' visibility based on the
     * current state, and shows the custom message when no filter is available
     * for the selected model.
     *
     * The filter can be saved if one of those conditions is matched:
     * - No favorite filter is currently set
     * - User emptied the input
     * - User changed the domain when favorite filter is set
     * - The input is currently being edited, known by the "this.state.isFloating" variable
     *
     * @private
     */
    _updateFilterIcons() {
        const el = document.querySelector(".o_mass_mailing_filter_container");
        if (!el || this.props.readonly) {
            return;
        }
        const filterCount = this.props.mailingFilterCount;
        const dropdown = document.querySelector(
            ".o_field_mailing_filter > .o_field_many2one_selection > .o_input_dropdown"
        );
        if (dropdown) {
            dropdown.classList.toggle("d-none", !filterCount);
        }
        // By default, domains in recordData are in string format, but adding / removing a leaf from domain widget converts
        // value into object, so we use 'Domain' class to convert them in same (string) format, allowing proper comparison.
        let recordDomain;
        let filterDomain;
        try {
            recordDomain = new Domain(this.props.mailingDomain || []).toString();
            filterDomain = new Domain(this.props.mailingFilterDomain || []).toString();
        } catch {
            // Don't raise a traceback if a domain set manually doesn't match the format expected.
            // This can happen when we unfocus the domain editor
            this.filter.canSaveFilter = false;
            this.filter.canRemoveFilter = false;
            return;
        }

        const modelFieldElement =
            this.props.modelField &&
            document.querySelector(
                `input#${this.props.modelField},div [name="${this.props.modelField}"]`
            );

        let value = "";
        if (modelFieldElement && modelFieldElement.tagName === "span") {
            value = modelFieldElement.textContent;
        } else if (modelFieldElement && modelFieldElement.tagName === "input") {
            value = modelFieldElement.value;
        }

        el.classList.toggle("d-none", recordDomain === "[]");
        this.filter.canSaveFilter =
            !this.props.mailingFilterId ||
            !!value.length ||
            this.state.isFloating ||
            filterDomain !== recordDomain;
        this.filter.canRemoveFilter = !this.filter.canSaveFilter;
    }

    // HANDLERS

    /**
     * Focus the 'Save' button on 'Tab' key, or directly save the filter on 'Enter'
     *
     * @param {KeyboardEvent} ev
     */
    onFilterNameInputKeydown(ev) {
        const btnSave = document.querySelector(".o_mass_mailing_btn_save_filter");
        if (ev.key === "Tab") {
            ev.preventDefault();
            btnSave.focus();
        } else if (ev.key === "Enter") {
            btnSave.click();
        }
    }

    /**
     * Deletes the saved filter, but we do not reset the applied domain
     * in this case.
     *
     * @param {Event} ev
     */
    async onRemoveFilter(ev) {
        const filterId = this.props.mailingFilterId[0];
        const mailingDomain = this.props.mailingDomain;
        // Prevent multiple clicks to avoid trying to deleting same record multiple times.
        ev.target.disabled = true;

        await this.orm.unlink("mailing.filter", [filterId]);
        this.update(false);
        this.props.updateMailingDomain(mailingDomain);
    }

    /**
     * Creates a new favorite filter, with the name provided from drop-down and
     * with the 'up to date' domain. If the input is blank, displays the warning
     * and keeps the popup open by preventing event propagation.
     *
     * Note: We do not disable the save button here to avoid multiple clicks as for the delete,
     * because as soon as the 'Save' button is clicked, the popup will be closed immediately.
     *
     * @param {Event} ev
     */
    async onSaveFilter(ev) {
        const filterInput = document.querySelector("input.o_mass_mailing_filter_name");
        const filterName = filterInput.value.trim();
        if (filterName.length === 0) {
            this.notification.add(_t("Please provide a name for the filter"), { type: "danger" });
            // Keep the drop-down open, and re-focus the input
            ev.stopPropagation();
            filterInput.focus();
        } else {
            const [newFilterId] = await this.env.model.orm.create("mailing.filter", [
                {
                    name: filterName,
                    mailing_domain: this.props.mailingDomain,
                    mailing_model_id: this.props.modelField[0],
                },
            ]);
            this.update([newFilterId, filterName]);
        }
    }
}

export class FieldMany2OneMailingFilter extends Component {
    static template = "mass_mailing.FieldMany2OneMailingFilter";
    static components = { Many2OneMailingFilter };
    static props = {
        ...Many2OneField.props,
        domain_field: { type: String, optional: true },
        model_field: { type: String, optional: true },
    };
    static defaultProps = {
        ...Many2OneField.defaultProps,
        domain_field: "mailing_domain",
        model_field: "mailing_model_id",
    };

    get m2oProps() {
        const p = computeM2OProps(this.props);
        return {
            ...p,
            mailingDomain: this.props.record.data[this.props.domain_field],
            mailingFilterCount: this.props.record.data.mailing_filter_count,
            mailingFilterDomain: this.props.record.data.mailing_filter_domain,
            mailingFilterId: this.props.record.data.mailing_filter_id,
            modelField: this.props.model_field,
            updateMailingDomain: (value) =>
                this.props.record.update({ [this.props.domain_field]: value }),
        };
    }
}

registry.category("fields").add("mailing_filter", {
    ...buildM2OFieldDescription(FieldMany2OneMailingFilter),
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            domain_field: staticInfo.options.domain_field,
            model_field: staticInfo.options.model_field,
        };
    },
    supportedOptions: [
        ...m2oSupportedOptions,
        {
            label: _t("Domain field"),
            name: "domain_field",
            type: "field",
            availableTypes: ["char"],
        },
        {
            label: _t("Model field"),
            name: "model_field",
            type: "field",
            availableTypes: ["char"],
        },
    ],
});
