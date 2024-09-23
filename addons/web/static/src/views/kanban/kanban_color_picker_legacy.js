import { ColorList } from "@web/core/colorlist/colorlist";
import { patch } from "@web/core/utils/patch";
import { createElement } from "@web/core/utils/xml";

import { LEGACY_KANBAN_BOX_ATTRIBUTE, KanbanArchParser } from "./kanban_arch_parser";
import { KanbanCompiler } from "./kanban_compiler";
import { KanbanRecord, getColorIndex } from "./kanban_record";

// TODO: remove this backward compatibility layer post v18

patch(KanbanArchParser.prototype, {
    parse(xmlDoc, models, modelName) {
        const archInfo = super.parse(xmlDoc, models, modelName);

        // Color and color picker (first node found is taken for each)
        const legacyCardDoc = archInfo.templateDocs[LEGACY_KANBAN_BOX_ATTRIBUTE];
        if (legacyCardDoc) {
            const cardColorEl = legacyCardDoc.querySelector("[color]");
            const cardColorField = cardColorEl && cardColorEl.getAttribute("color");

            const colorEl = xmlDoc.querySelector("templates .oe_kanban_colorpicker[data-field]");
            const colorField = (colorEl && colorEl.getAttribute("data-field")) || "color";

            archInfo.cardColorField = archInfo.cardColorField || cardColorField;
            archInfo.colorField = colorField;
        }

        return archInfo;
    },
});

patch(KanbanCompiler.prototype, {
    setup() {
        super.setup();
        this.compilers.push({ selector: ".oe_kanban_colorpicker", fn: this.compileColorPicker });
    },

    /**
     * @returns {Element}
     */
    compileColorPicker() {
        return createElement("t", {
            "t-call": "web.KanbanColorPicker",
            "t-call-context": "__comp__",
        });
    },
});

/**
 * Returns the class name of a record according to its color.
 */
function getColorClass(value) {
    return `oe_kanban_color_${getColorIndex(value)}`;
}

/**
 * Returns the proper translated name of a record color.
 */
function getColorName(value) {
    return ColorList.COLORS[getColorIndex(value)];
}

patch(KanbanRecord.prototype, {
    selectColor(colorIndex) {
        const { archInfo, record } = this.props;
        return record.update({ [archInfo.colorField]: colorIndex }, { save: true });
    },

    get renderingContext() {
        return Object.assign(super.renderingContext, {
            kanban_color: getColorClass,
            kanban_getcolor: getColorIndex,
            kanban_getcolorname: getColorName,
        });
    },
});
