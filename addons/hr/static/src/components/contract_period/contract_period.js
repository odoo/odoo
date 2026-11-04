import { Component, computed, useProps } from "@odoo/owl";

import { today } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatDate } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Return the contract to display among the given ones: the ongoing contract,
 * else the next one to start, else the last one.
 *
 * @param {{ start: luxon.DateTime|false, end: luxon.DateTime|false }[]} contracts
 * @param {luxon.DateTime} day
 * @returns {{ start: luxon.DateTime, end: luxon.DateTime|false }|undefined}
 */
export function getDisplayedContract(contracts, day) {
    const sortedContracts = contracts
        .filter((contract) => contract.start)
        .sort((a, b) => a.start - b.start);
    return (
        sortedContracts.find(
            (contract) => contract.start <= day && (!contract.end || contract.end >= day)
        ) ||
        sortedContracts.find((contract) => contract.start > day) ||
        sortedContracts.at(-1)
    );
}

/**
 * Contract line of the employee kanban card, set on ``version_ids``.
 */
export class ContractPeriodField extends Component {
    static template = "hr.ContractPeriodField";
    props = useProps(standardFieldProps);

    contract = computed(() => {
        const versions = this.props.record.data[this.props.name].records;
        const contracts = versions.map((version) => ({
            start: version.data.contract_date_start,
            end: version.data.contract_date_end,
        }));
        return getDisplayedContract(contracts, today());
    });

    formatDate(date) {
        return formatDate(date);
    }

    isEnded(contract) {
        return contract.end && contract.end < today();
    }
}

export const contractPeriodField = {
    component: ContractPeriodField,
    displayName: _t("Contract Period"),
    supportedTypes: ["one2many"],
    relatedFields: [
        { name: "contract_date_start", type: "date" },
        { name: "contract_date_end", type: "date" },
    ],
};

registry.category("fields").add("contract_period", contractPeriodField);
