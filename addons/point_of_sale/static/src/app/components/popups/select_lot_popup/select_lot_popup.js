import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useAutoFocusToLast } from "@point_of_sale/app/hooks/hooks";
import { LotAutoComplete } from "@point_of_sale/app/components/popups/select_lot_popup/lot_autocomplete/lot_autocomplete";

export class SelectLotPopup extends Component {
    static template = "point_of_sale.SelectLotPopup";
    static components = { Dialog, LotAutoComplete };
    static props = {
        array: Array,
        isSingleItem: Boolean,
        title: String,
        name: String,
        getPayload: Function,
        close: Function,
        options: { type: Array, optional: true },
        customInput: { type: Boolean, optional: true },
        uniqueValues: { type: Boolean, optional: true },
        isLotNameUsed: { type: Function, optional: true },
    };

    setup() {
        this._id = 0;
        this.state = useState({
            value: this.props.isSingleItem ? this.props.array[0]?.text : "",
            values: this.props.array
                .filter((item) => item.text.trim() !== "")
                .map((item) => ({
                    text: item.text.trim(),
                    id: item.id,
                })),
        });
        useAutoFocusToLast();
        this.notification = useService("notification");
    }
    _nextId() {
        return this._id++;
    }
    getSources() {
        return [
            {
                options: (currentInput) => {
                    const filteredOptions = this.props.options.filter(
                        (option) =>
                            option.name.includes(currentInput) &&
                            !this.state.values.some((value) => value.text === option.name)
                    );
                    return filteredOptions.length
                        ? filteredOptions.map((option) => ({
                              label: option.name,
                              id: option.id,
                              create: true,
                          }))
                        : this.props.customInput && currentInput
                        ? [
                              {
                                  label: _t("Create serial/lot number..."),
                                  currentInput: currentInput,
                                  create: true,
                              },
                          ]
                        : [
                              {
                                  label: _t("No existing serial/lot number matching..."),
                                  create: false,
                              },
                          ];
                },
            },
        ];
    }
    onSelect(...x) {
        const lot = x[0];
        if (!lot.create || (!this.props.customInput && !this.props.options.includes(lot))) {
            return this.notification.add({
                message: _t("The serial/lot number is not valid."),
                type: "danger",
            });
        }
        const newItem = lot.currentInput
            ? { text: lot.currentInput }
            : { text: lot.label, id: lot.id };
        this.state.values = this.props.isSingleItem ? [newItem] : [...this.state.values, newItem];
        this.state.value = this.props.isSingleItem ? newItem.text : "";
    }

    removeItem(id) {
        this.state.values = this.state.values.filter((item) => item.id !== id);
    }
    confirm() {
        const finalValues = new Set();
        const filteredValues = this.state.values
            .filter((item) => {
                const itemValue = item.text.trim();
                const isValidValue =
                    itemValue !== "" &&
                    !this.props.isLotNameUsed(itemValue) &&
                    (this.props.customInput || this.props.options.includes(itemValue));

                if (!isValidValue) {
                    return false;
                }

                if (this.props.uniqueValues) {
                    if (finalValues.has(itemValue)) {
                        return false;
                    }
                    finalValues.add(itemValue);
                }

                return true;
            })
            .map((item) => ({
                text: item.text,
                _id: this._nextId(),
                ...(this.props.array.some((lot) => lot.text == item.text) ? { id: item.id } : {}),
            }));
        this.props.getPayload(filteredValues);
        this.props.close();
    }
}
