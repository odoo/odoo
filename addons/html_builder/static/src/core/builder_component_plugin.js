import { BuilderList } from "@html_builder/core/building_blocks/builder_list";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { BuilderButtonGroup } from "./building_blocks/builder_button_group";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { BuilderDateTimePicker } from "./building_blocks/builder_datetimepicker";
import { BuilderRow } from "./building_blocks/builder_row";
import { BuilderButton } from "./building_blocks/builder_button";
import { BuilderNumberInput } from "./building_blocks/builder_number_input";
import { BuilderSelect } from "./building_blocks/builder_select";
import { BuilderSelectItem } from "./building_blocks/builder_select_item";
import { BuilderColorPicker } from "./building_blocks/builder_colorpicker";
import { BuilderTextInput } from "./building_blocks/builder_text_input";
import { BuilderCheckbox } from "./building_blocks/builder_checkbox";
import { BuilderRange } from "./building_blocks/builder_range";
import { BuilderContext } from "./building_blocks/builder_context";
import { BasicMany2Many } from "./building_blocks/basic_many2many";
import { BuilderMany2Many } from "./building_blocks/builder_many2many";
import { BuilderMany2One } from "./building_blocks/builder_many2one";
import { ModelMany2Many } from "./building_blocks/model_many2many";
import { Plugin } from "@html_editor/plugin";
import { Img } from "./img";
import { BuilderUrlPicker } from "./building_blocks/builder_urlpicker";
import { BuilderFontFamilyPicker } from "./building_blocks/builder_fontfamilypicker";

export class BuilderComponentPlugin extends Plugin {
    static id = "builderComponents";
    static shared = ["getComponents"];

    resources = {
        builder_components: {
            BuilderContext,
            BuilderFontFamilyPicker,
            BuilderRow,
            BuilderUrlPicker,
            Dropdown,
            DropdownItem,
            BuilderButtonGroup,
            BuilderButton,
            BuilderTextInput,
            BuilderNumberInput,
            BuilderRange,
            BuilderColorPicker,
            BuilderSelect,
            BuilderSelectItem,
            BuilderCheckbox,
            BasicMany2Many,
            BuilderMany2Many,
            BuilderMany2One,
            ModelMany2Many,
            BuilderDateTimePicker,
            BuilderList,
            Img,
        },
    };

    setup() {
        this.Components = {};
        for (const r of this.getResource("builder_components")) {
            for (const C in r) {
                if (C in this.Components) {
                    throw new Error(`Duplicated builder component: ${C}`);
                }
                this.Components[C] = r[C];
            }
        }
    }

    getComponents() {
        return this.Components;
    }
}
