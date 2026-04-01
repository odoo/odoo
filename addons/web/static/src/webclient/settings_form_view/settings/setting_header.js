import { Setting } from "@web/views/form/setting/setting";

export class SettingHeader extends Setting {
    static template = "web.HeaderSetting";

    get classNames() {
        const { class: _class } = this.props;
        const classNames = {
            app_settings_header: true,
            "d-flex": true,
            "flex-column": true,
            "flex-md-row": true,
            "align-items-baseline": true,
            "gap-1": true,
            "gap-md-5": true,
            "py-3": true,
            "bg-opacity-25": true,
            [_class]: Boolean(_class),
        };
        return classNames;
    }

    get labelString() {
        return this.props.string || this.props.record.fields[this.props.name]?.string || "";
    }
}
