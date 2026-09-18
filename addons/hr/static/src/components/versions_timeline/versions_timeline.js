import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { Domain } from "@web/core/domain";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { statusBarField, StatusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { _t } from "@web/core/l10n/translation";
import { signal } from "@odoo/owl";

export class VersionsTimeline extends StatusBarField {
    static template = "hr.VersionsTimeline";

    datetimePickerTargetRef = signal.ref();

    /** @override **/
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");

        this.dateTimePicker = useDateTimePicker({
            target: this.datetimePickerTargetRef,
            onApply: (date) => {
                if (date) {
                    this.createVersion(date);
                }
            },
            get pickerProps() {
                return { type: "date" };
            },
        });
    }

    get showAddButton() {
        return !("active" in this.props.record.fields) || this.props.record.data.active;
    }

    /** @override **/
<<<<<<< e264fedcb3dbc4d2e2d3511ff86f4dd104e63228
    getDomain(props) {
        return Domain.and([
            super.getDomain(props),
            [["employee_id", "=", props.record.evalContext.id]],
        ]).toList();
||||||| e4e3aa3283c36f6f6bf97e5a824b411805edd839
    getDomain() {
        return Domain.and([super.getDomain(),
            [["employee_id", "=", this.props.record.evalContext.id]]]
        ).toList()
=======
    getDomain() {
        const { record } = this.props;
        const additionalDomains = [[["employee_id", "=", record.evalContext.id]]];
        if ("active" in record.fields && !record.data.active) {
            additionalDomains.push([["active", "=", false]]);
        }
        return Domain.and([super.getDomain(), ...additionalDomains]).toList();
>>>>>>> 2b9c70a07138ed4f7ece787759fb5bb479e10f70
    }

    /** @override **/
    getFieldNames(props) {
        const fieldNames = super.getFieldNames(props);
        fieldNames.push("employee_type_id", "contract_date_start", "contract_date_end");
        return fieldNames.filter((fName) => fName in props.record.fields);
    }

    displayContractLines() {
        return ["employee_type_id", "contract_date_start", "contract_date_end"].every(
            (fieldName) => fieldName in this.props.record.fields
        );
    }

    isContractLineContinued(index) {
        const item = this.items.inline[index];
        const nextItem = this.items.inline[index + 1];
        return Boolean(
            item?.isInContract &&
                item.isCurrentContract &&
                nextItem?.isInContract &&
                nextItem.isCurrentContract
        );
    }

    async createVersion(date) {
        await this.props.record.save();
        const version_id = await this.orm.call("hr.employee", "create_version", [
            this.props.record.evalContext.id,
            { date_version: date },
        ]);

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
        function format(dateString) {
            return luxon.DateTime.fromISO(dateString).toFormat("MMM dd, yyyy");
        }
        const items = super.getAllItems();
        if (!this.displayContractLines()) {
            return items;
        }
        const dataById = new Map(this.specialData.data.map((d) => [d.id, d]));

        const selectedVersion = items.find((item) => item.isSelected)?.value;
        const selectedContractDate = dataById.get(selectedVersion)?.contract_date_start;

        return items.map((item, index) => {
            const itemSpecialData = dataById.get(item.value) || {};
            const contractDateStart = itemSpecialData.contract_date_start;
            let contractDateEnd = itemSpecialData.contract_date_end;
            contractDateEnd = contractDateEnd ? format(contractDateEnd) : _t("Indefinite");
            const employeeType = itemSpecialData.employee_type_id?.[1] ?? _t("Contract");
            const toolTip = contractDateStart
                ? `${employeeType}: ${format(contractDateStart)} - ${contractDateEnd}`
                : _t("No contract");

            return {
                ...item,
                isCurrentContract: contractDateStart === selectedContractDate,
                isInContract: Boolean(contractDateStart),
                toolTip,
            };
        });
    }

    /** @override **/
    getSortedItems() {
        const sorted = super.getSortedItems();

        sorted.inline.sort((a, b) => {
            const dateA = luxon.DateTime.fromFormat(a.label, "MMM d, yyyy");
            const dateB = luxon.DateTime.fromFormat(b.label, "MMM d, yyyy");

            return dateB.toMillis() - dateA.toMillis();
        });

        return sorted;
    }
}

export const versionsTimeline = {
    ...statusBarField,
    component: VersionsTimeline,
    additionalClasses: ["o_field_statusbar", "o_records_timeline", "d-flex", "gap-1"],
};

registry.category("fields").add("versions_timeline", versionsTimeline);
