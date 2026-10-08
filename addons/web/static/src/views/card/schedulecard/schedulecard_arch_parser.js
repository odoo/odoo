import { parseXML } from "@web/core/utils/xml";
import {
    addFieldDependencies,
    extractFieldsFromArchInfo,
} from "@web/model/relational_model/utils";
import { CardArchParser } from "@web/views/card/card_arch_parser";

const DEFAULT_SCHEDULECARD_ARCH = `
    <schedulecard>
        <templates>
            <t t-name="card"><field name="display_name" class="text-truncate"/></t>
        </templates>
    </schedulecard>`;

/**
 * Parses the <schedulecard> node of a view (e.g. calendar, gantt), used to
 * render the records of its "to schedule" side panel. When the view has no
 * such node, a default card displaying the display_name is used.
 *
 * @param {Element} [node] the <schedulecard> node, if any
 * @param {Object} models
 * @param {string} modelName
 * @returns {{ archInfo: Object, activeFields: Object, fields: Object }}
 */
export function parseScheduleCard(node, models, modelName) {
    node ||= parseXML(DEFAULT_SCHEDULECARD_ARCH);
    const archInfo = new CardArchParser().parse(node, models, modelName);
    // cursor-pointer marks the card as clickable, like kanban records: it brings
    // the hovered card above its neighbours (see web_enterprise card.scss)
    if (archInfo.cardClassName) {
        archInfo.cardClassName += " cursor-pointer";
    } else {
        archInfo.cardClassName = "cursor-pointer";
    }
    const { activeFields, fields } = extractFieldsFromArchInfo(
        archInfo,
        models[modelName].fields
    );
    // display_name is always fetched, whatever the card template: it is used
    // as title when dragging the records and when opening them in a dialog
    addFieldDependencies(activeFields, fields, [{ name: "display_name", type: "char" }]);
    return { archInfo, activeFields, fields };
}
