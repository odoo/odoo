/** @odoo-module **/

import { DynamicPlaceholderPopover } from "@web/views/fields/dynamic_placeholder_popover";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";

export class StudioDynamicPlaceholderPopover extends DynamicPlaceholderPopover {
    static template = "web_studio.StudioDynamicPlaceholderPopover";
    static props = [...DynamicPlaceholderPopover.props, "showOnlyX2ManyFields"];
    setup() {
        super.setup();
        this.loadFieldInfo = useLoadFieldInfo();
    }

    _loadAllowedExpressions() {}

    filter(fieldDef) {
        if (this.props.showOnlyX2ManyFields) {
            return ["one2many", "many2many"].includes(fieldDef.type);
        } else {
            /**
             * We don't want to display x2many fields inside a report as it would not make sense.
             * We also don't want to display boolean fields.
             * This override is necessary because we want to be able to select non-searchable fields.
             * There is no reason as to why this wouldn't be allowed inside a report as we don't search on those fields,
             * we simply render them.
             */
            return !["one2many", "boolean", "many2many"].includes(fieldDef.type);
        }
    }

    async validate() {
        const fieldInfo = (await this.loadFieldInfo(this.props.resModel, this.state.path)).fieldDef;
        const filename_exists = (
            await this.loadFieldInfo(this.props.resModel, this.state.path + "_filename")
        ).fieldDef;
        const is_image = fieldInfo.type == "binary" && !filename_exists;
        this.props.validate(
            this.state.path,
            this.state.defaultValue,
            is_image,
            fieldInfo.relation,
            fieldInfo.string
        );
        this.props.close();
    }
}
