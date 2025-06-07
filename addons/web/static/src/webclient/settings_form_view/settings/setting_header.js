import { Setting } from "@web/views/form/setting/setting";

export class SettingHeader extends Setting {
    static template = "web.HeaderSetting";
    get labelString() {
        return this.props.string || this.props.record.fields[this.props.name].string;
    }
}
