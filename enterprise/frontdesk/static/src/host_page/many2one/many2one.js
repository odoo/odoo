/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Component } from "@odoo/owl";

export class Many2One extends Component {
    static template = "frontdesk.Many2One";
    static components = { AutoComplete };
    static props = {
        disableButton: Function,
        stationId: Number,
        token: String,
        update: Function,
    };

    async loadOptionsSource(request) {
        if (this.lastProm) {
            this.lastProm.abort(false);
        }
        this.lastProm = this.search(request);
        const records = await this.lastProm;
        if (!records.length) {
            this.props.disableButton(true);
        }
        const options = records.map((result) => this.mapRecordToOption(result));
        return options;
    }

    mapRecordToOption(result) {
        return {
            value: result[0],
            label: result[1].split("\n")[0],
            displayName: result[1],
        };
    }

    /* This method triggers when a user select a option */
    onSelect(option, params = {}) {
        const record = {
            id: option.value,
            display_name: option.displayName,
        };
        if (record) {
            this.props.disableButton(false);
        }
        params.input.value = option.displayName;
        this.props.update(record);
    }

    /* This method triggers when a user types in the input field */
    search(name) {
        return rpc(`/frontdesk/${this.props.stationId}/${this.props.token}/get_hosts`, {
            name: name,
        });
    }

    get sources() {
        return [this.optionsSource];
    }

    get optionsSource() {
        return {
            placeholder: _t("Loading..."),
            options: this.loadOptionsSource.bind(this),
            optionTemplate: "avatarAutoComplete",
        };
    }
}
