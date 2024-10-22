import { DatePickerPopup } from "@point_of_sale/app/utils/date_picker_popup/date_picker_popup";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class ShipLater extends DatePickerPopup {
    static template = "l10n_in_pos.ShipLater";
    static components = {
        ...DatePickerPopup.components,
        AutoComplete,
    };
    static props = {
        ...DatePickerPopup.props,
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.posData = this.getPlaceOfSupply;
    }

    loadOptionsSource(request) {
        const inputValue = request?.toLowerCase();
        const records = this.posData.map(({ id, name }) => [id, name]);
        const filteredRecords = inputValue
            ? records.filter(([_, name]) => name.toLowerCase().startsWith(inputValue))
            : records;
        return filteredRecords.map(this.mapRecordToOption);
    }

    mapRecordToOption([value, name]) {
        return {
            value,
            label: name.split("\n")[0],
            displayName: name,
        };
    }

    get getPlaceOfSupply() {
        const states = this.pos.models["res.country.state"].getAll();
        const l10n_in_state = [];
        for (const state of states) {
            if (state.country_id.code == "IN") {
                l10n_in_state.push({ id: state.id, name: state.name });
            }
        }
        return l10n_in_state;
    }

    get sources() {
        return [this.optionsSource];
    }

    get optionsSource() {
        return {
            options: this.loadOptionsSource.bind(this),
        };
    }

    get defaultValue() {
        return this.pos.company.state_id.name;
    }

    onSelect(option, params = {}) {
        this.selectedStateId = this.pos.models["res.country.state"].get(option.value);
        params.input.value = option.displayName;
    }

    confirm() {
        this.props.getPayload(
            this.state.shippingDate < this._today() ? this._today() : this.state.shippingDate,
            this.selectedStateId ? this.selectedStateId : this.pos.company.state_id
        );
        this.props.close();
    }
}
