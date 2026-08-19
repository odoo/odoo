import { formatMonetary } from "@web/views/fields/formatters";
import { formatFloat } from "@web/core/utils/numbers";
import { parseFloat } from "@web/views/fields/parsers";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { DropdownPopover } from "@web/core/dropdown/_behaviours/dropdown_popover";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import {
    Component,
    computed,
    onPatched,
    onWillStart,
    signal,
    toRaw,
    proxy,
    useEffect,
    useProps,
} from "@odoo/owl";
import { useNumpadDecimal } from "@web/views/fields/numpad_decimal_hook";

/**
 A line of some TaxTotalsComponent, giving the values of a tax group.
 **/
class TaxGroupComponent extends Component {
    static props = {
        totals: { optional: true },
        subtotal: { optional: true },
        taxGroup: { optional: true },
        onChangeTaxGroup: { optional: true },
        isReadonly: Boolean,
        invalidate: Function,
        removeCashRounding: { type: Function, optional: true },
    };
    static template = "account.TaxGroupComponent";

    inputTaxRef = signal.ref();
    numpadDecimalRef = signal.ref();

    setup() {
        this.state = proxy({ value: "readonly" });
        onPatched(() => {
            if (this.state.value === "edit") {
                const el = this.inputTaxRef();
                if (!el) {
                    return;
                }
                const { taxGroup } = this.props;
                const newVal = formatFloat(taxGroup.tax_amount_currency, { digits: this.props.totals.currency_pd });
                el.value = newVal;
                el.focus(); // Focus the input
            }
        });
        useEffect(() => {
            this.props.taxGroup;
            this.setState("readonly");
        });
        useNumpadDecimal(this.numpadDecimalRef);
    }

    formatMonetary(value) {
        return formatMonetary(value, {currencyId: this.props.totals.currency_id});
    }

    //--------------------------------------------------------------------------
    // Main methods
    //--------------------------------------------------------------------------

    /**
     * The purpose of this method is to change the state of the component.
     * It can have one of the following three states:
     *  - readonly: display in read-only mode of the field,
     *  - edit: display with a html input field,
     *  - disable: display with a html input field that is disabled.
     *
     * If a value other than one of these 3 states is passed as a parameter,
     * the component is set to readonly by default.
     *
     * @param {String} value
     */
    setState(value) {
        if (["readonly", "edit", "disable"].includes(value)) {
            this.state.value = value;
        }
        else {
            this.state.value = "readonly";
        }
    }

    /**
     * This method handles the "_onChangeTaxValue" event. In this method,
     * we get the new value for the tax group, we format it and we call
     * the method to recalculate the tax lines. At the moment the method
     * is called, we disable the html input field.
     *
     * In case the value has not changed or the tax group is equal to 0,
     * the modification does not take place.
     */
    _onChangeTaxValue() {
        this.setState("disable"); // Disable the input
        const oldValue = this.props.taxGroup.tax_amount_currency;
        const el = this.inputTaxRef();
        if (!el) {
            return;
        }
        let newValue;
        try {
            newValue = parseFloat(el.value); // Get the new value
        } catch {
            el.value = oldValue;
            this.setState("edit");
            return;
        }
        // The newValue can"t be equals to 0
        if (newValue === oldValue || newValue === 0) {
            this.setState("readonly");
            return;
        }
        const deltaValue = newValue - oldValue;
        this.props.taxGroup.tax_amount_currency += deltaValue;
        this.props.subtotal.tax_amount_currency += deltaValue;
        this.props.totals.tax_amount_currency += deltaValue;
        this.props.totals.total_amount_currency += deltaValue;

        this.props.onChangeTaxGroup({
            oldValue,
            newValue: newValue,
            taxGroupId: this.props.taxGroup.id,
        });
    }
}

/**
 Widget used to display tax totals by tax groups for invoices, PO and SO,
 and possibly allowing editing them.

 Note that this widget requires the object it is used on to have a
 currency_id field.
 **/
export class TaxTotalsComponent extends Component {
    static template = "account.TaxTotalsField";
    static components = { TaxGroupComponent };

    props = useProps(standardFieldProps);

    totals = computed(() => this.formatData(this.props));

    taxGroupWithRoundingAmount = computed(() => {
        const totals = this.totals();
        if (!totals || !this.props.record.data.has_biggest_tax_cash_rounding_line) {
            return;
        }
        const taxGroups = totals.subtotals?.flatMap((subtotal) => subtotal.tax_groups);
        if (taxGroups?.length) {
            return taxGroups.reduce((a, b) =>
                b.tax_amount_currency > a.tax_amount_currency ? b : a
            );
        }
    });

    setup() {
        this.orm = useService("orm");
        this.dialogService = useService("dialog");
        this.cashRoundingDropdown = usePopover(DropdownPopover, {
            popoverClass: "o-dropdown--menu dropdown-menu o_cash_rounding_dropdown",
            position: "left-middle",
            role: "menu",
        });
        this.groupCashRounding = false;

        onWillStart(async () => {
            this.groupCashRounding = await user.hasGroup("account.group_cash_rounding");
        });
    }

    //--------------------------------------------------------------------------
    // Cash rounding
    //--------------------------------------------------------------------------

    get showCashRounding() {
        const move = this.props.record.data;
        return (
            this.groupCashRounding && move.move_type?.startsWith("out_") && move.state === "draft"
        );
    }

    isCashRoundingSelected(cashRoundingId) {
        return cashRoundingId === this.props.record.data.invoice_cash_rounding_id.id;
    }

    setCashRounding(cashRoundingId) {
        this.cashRoundingDropdown.close();
        this.props.record.update({
            ["invoice_cash_rounding_id"]: {
                id: this.isCashRoundingSelected(cashRoundingId) ? false : cashRoundingId,
            },
        });
        this.props.record.save();
    }

    async openCashRoundingDropdown(target) {
        if (this.cashRoundingDropdown.isOpen) {
            this.cashRoundingDropdown.close();
            return;
        }

        const { total_length, records } = await this.orm.call(
            "account.move",
            "get_cash_roundings",
            [this.props.record.data.id]
        );
        const items = [
            {
                id: "title",
                label: _t("Rounding Methods"),
                class: "o_cash_rounding_dropdown_title",
                onSelected: () => {},
            },
        ];
        items.push(
            ...records.map((rounding) => ({
                id: rounding.id,
                label: rounding.display_name,
                class: {
                    o_cash_rounding_dropdown_selected: this.isCashRoundingSelected(rounding.id),
                },
                onSelected: () => this.setCashRounding(rounding.id),
            }))
        );
        if (total_length > records.length) {
            items.push({
                id: "search_more",
                label: _t("Search more..."),
                class: "o_cash_rounding_dropdown_action",
                onSelected: () => this.openCashRoundingListView(),
            });
        }
        items.push({
            id: "new_rounding",
            label: _t("Create and edit"),
            class: "o_cash_rounding_dropdown_action",
            onSelected: () => this.openCashRoundingFormView(),
        });
        this.cashRoundingDropdown.open(target, { items, slots: {} });
    }

    openCashRoundingFormView() {
        this.dialogService.add(FormViewDialog, {
            resModel: "account.cash.rounding",
            title: _t("New Rounding Method"),
            onRecordSaved: (record) => this.setCashRounding(record.resId),
        });
    }

    openCashRoundingListView() {
        this.dialogService.add(SelectCreateDialog, {
            resModel: "account.cash.rounding",
            title: _t("Select Rounding Method"),
            multiSelect: false,
            onSelected: (resIds) => this.setCashRounding(resIds[0]),
        });
    }

    removeCashRounding() {
        return this.props.record.update({ ["invoice_cash_rounding_id"]: false });
    }

    //--------------------------------------------------------------------------

    get readonly() {
        return this.props.readonly;
    }

    invalidate() {
        return this.props.record.setInvalidField(this.props.name);
    }

    formatMonetary(value) {
        return formatMonetary(value, {currencyId: this.totals().currency_id});
    }

    /**
     * This method is the main function of the tax group widget.
     * It is called by the TaxGroupComponent and receives the newer tax value.
     *
     * It is responsible for triggering an event to notify the ORM of a change.
     */
    _onChangeTaxValueByTaxGroup({ oldValue, newValue }) {
        if (oldValue === newValue) return;
        const totals = this.totals();
        this.props.record.update({ [this.props.name]: totals });
        delete totals.cash_rounding_base_amount_currency;
    }

    formatData(props) {
        let totals = JSON.parse(JSON.stringify(toRaw(props.record.data[this.props.name])));
        if (!totals) {
            return;
        }
        return totals;
    }
}

export const taxTotalsComponent = {
    component: TaxTotalsComponent,
};

registry.category("fields").add("account-tax-totals-field", taxTotalsComponent);
