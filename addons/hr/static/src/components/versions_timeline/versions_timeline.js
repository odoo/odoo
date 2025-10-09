import { onWillUpdateProps, useComponent, useState } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { getFieldDomain, useRecordObserver } from "@web/model/relational_model/utils";
import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { _t } from "@web/core/l10n/translation";

export class VersionsTimeline extends StatusBarField {
    static template = "hr.VersionsTimeline";

    /** @override **/
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");

        if (this.field.type === "many2one") {
            this.specialData = useSpecialDataNoCache((orm, props) => {
                const { foldField, name: fieldName, record } = props;
                const { relation } = record.fields[fieldName];
                const fieldNames = ["display_name", "contract_type_id", "contract_date_start", "contract_date_end"];
                if (foldField) {
                    fieldNames.push(foldField);
                }
                const value = record.data[fieldName];
                let domain = getFieldDomain(record, fieldName, props.domain);
                domain = Domain.and([
                    [["employee_id", "=", props.record.evalContext.id]],
                    domain,
                ]).toList();
                if (domain.length && value) {
                    domain = Domain.or([[["id", "=", value.id]], domain]).toList(
                        record.evalContext
                    );
                }
                return orm.searchRead(relation, domain, fieldNames);
            });
        }

        this.dateTimePicker = useDateTimePicker({
            target: `datetime-picker-target-version`,
            onApply: (date) => {
                if (date) this.createVersion(date);
            },
            get pickerProps() {
                return { type: "date" };
            },
        });
    }

    async createVersion(date) {
        const version_id = await this.orm.call("hr.employee", "create_version", [
            this.props.record.evalContext.id,
            { date_version: date },
        ]);

        const { record } = this.props;
        await record.save();
        await this.props.record.model.load({
            context: {
                ...this.props.record.model.env.searchModel.context,
                version_id: version_id,
            },
        });
    }

    onClickDateTimePickerBtn() {
        this.dateTimePicker.open();
    }

    /** @override **/
    async selectItem(item) {
        const { record } = this.props;
        await record.save();
        await this.props.record.model.load({
            context: {
                ...this.props.record.model.env.searchModel.context,
                version_id: item.value,
            },
        });
    }

    /** @override **/
    getAllItems() {
        const items = super.getAllItems();

        const dataById = new Map(this.specialData.data.map(d => [d.id, d]));

        const selectedVersion = items.find(item => item.isSelected)?.value;
        const selectedContractDate = dataById.get(selectedVersion)?.contract_date_start;

        // This gets the index of the first and last occurrence per contract.
        const groups = new Map(); // key: contract_date_start -> { firstIdx, lastIdx }
        items.forEach((item, index) => {
            const itemSpecialData = dataById.get(item.value);
            const start = itemSpecialData?.contract_date_start;
            if (start) {
                const group = groups.get(start);
                if (!group) {
                    groups.set(start, { firstIdx: index, lastIdx: index });
                } else {
                    group.lastIdx = index;
                }
            }
        });

        return items.map((item, index) => {
            const itemSpecialData = dataById.get(item.value) || {};
            const contractDateStart = itemSpecialData.contract_date_start;
            let contractDateEnd = itemSpecialData.contract_date_end;
            contractDateEnd = contractDateEnd ? contractDateEnd : _t("Indefinite");
            const contractType = itemSpecialData.contract_type_id?.[1] ?? _t("Contract");
            const toolTip = contractDateStart
                ? `${contractType}: ${contractDateStart} - ${contractDateEnd}`
                : _t("No contract");

            const group = contractDateStart ? groups.get(contractDateStart) : null;
            const isFirstOfContract = !!group && group.firstIdx === index;
            const isLastOfContract  = !!group && group.lastIdx  === index;

            return {
                ...item,
                isCurrentContract: contractDateStart === selectedContractDate,
                isInContract: Boolean(contractDateStart),
                isFirstOfContract,
                isLastOfContract,
                toolTip,
            };
        });
    }
}

export function useSpecialDataNoCache(loadFn) {
    const component = useComponent();
    const orm = component.env.services.orm;

    /** @type {{ data: Record<string, T> }} */
    const result = useState({ data: {} });
    useRecordObserver(async (record, props) => {
        result.data = await loadFn(orm, { ...props, record });
    });
    onWillUpdateProps(async (props) => {
        // useRecordObserver callback is not called when the record doesn't change
        if (props.record.id === component.props.record.id) {
            result.data = await loadFn(orm, props);
        }
    });
    return result;
}

export const versionsTimeline = {
    ...statusBarField,
    component: VersionsTimeline,
    additionalClasses: ["o_field_statusbar", "d-flex", "gap-1"],
};

registry.category("fields").add("versions_timeline", versionsTimeline);
