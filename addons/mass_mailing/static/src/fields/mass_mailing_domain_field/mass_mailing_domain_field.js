import { registry } from "@web/core/registry";
import { DomainField, domainField } from "@web/views/fields/domain/domain_field";
import { MassMailingDomainSelector } from "./mass_mailing_domain_selector";
import { useService } from "@web/core/utils/hooks";
import { onWillUpdateProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Domain } from "@web/core/domain";

/**
 * Domain field that toggles `use_exclusion_list` instead of
 * changing the domain to include archived records.
 */
export class MassMailingDomainField extends DomainField {
    static template = "mass_mailing.MassMailingDomainField";
    static props = {
        ...DomainField.props,
        ableToSave: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ...super.defaultProps,
        ableToSave: false,
    };
    static components = {
        DomainSelector: MassMailingDomainSelector,
    };

    setup() {
        super.setup();
        this.action = useService("action");
        this.isDomainChanged = false;
        onWillUpdateProps((np) => this.onPropsUpdated(np));
    }

    async onPropsUpdated(props) {
        if (!props.ableToSave) {
            return;
        }
        if (await this.isNewDomain(props)) {
            this.isDomainChanged = true;
        } else {
            this.isDomainChanged = false;
        }
    }

    /**
     * Check if the active domain (the domain which is currently being displayed in the
     * domain selector), is different than the domain of the selected dynamic list, if
     * one was selected.
     *
     * If no list was selected, check if the active domain has been edited.
     *
     * If multiple lists were selected, the domain is new (the combination
     * of all the lists' domains) and can be saved, unless it is equal to Domain.TRUE.
     *
     * @param {Object} newProps
     */
    async isNewDomain(newProps) {
        const activeDomain = new Domain(newProps.record.data[this.props.name] || "[]");
        const contactListIds = newProps.record.data.contact_list_ids.currentIds;
        if (activeDomain.toString() === Domain.TRUE.toString() || contactListIds.length == 0) {
            return false;
        }

        if (contactListIds.length > 1) {
            return true;
        }

        const mailing_lists = await this.orm.read("mailing.list", contactListIds, [
            "mailing_domain",
        ]);
        const domain = new Domain(mailing_lists[0].mailing_domain || []);
        const normalize = (d) => JSON.stringify(d.toList());

        return normalize(domain) !== normalize(activeDomain);
    }

    async onSaveDynamicListButtonClick() {
        const domain = this.getDomain();
        const resModel = this.getResModel();
        const action = await this.orm.call(
            "mailing.list",
            "get_dynamic_mailing_list_form_view_minimal",
            [[]],
            { model: resModel, domain: domain }
        );
        if (!action) {
            return;
        }
        this.action.doAction(action);
    }

    updateUseExclusionList(value) {
        this.props.record.update({ use_exclusion_list: value });
    }
}

export const massMailingDomainField = {
    ...domainField,
    component: MassMailingDomainField,
    supportedOptions: [
        ...domainField.supportedOptions,
        {
            label: _t("Display the save domain as dynamic list button"),
            name: "able_to_save",
            type: "boolean",
        },
    ],
    extractProps: (fieldInfo, dynamicInfo) => ({
        ...domainField.extractProps(fieldInfo, dynamicInfo),
        ableToSave: fieldInfo.options.able_to_save || false,
    }),
};

registry.category("fields").add("mass_mailing_domain", massMailingDomainField);
