/** @odoo-module **/

import { useChildSubEnv } from "@odoo/owl";
import { Setting } from "./setting";

export class SettingHeader extends Setting {
    setup() {
        super.setup();
        // Don't search on a header setting
        useChildSubEnv({ searchState: { value: "" } });
    }

    get labelString() {
        return this.props.string || this.props.record.fields[this.props.name].string;
    }
}
SettingHeader.template = "web.HeaderSetting";
