/** @odoo-module native */
import { getSectionRecords } from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { x2ManyCommands } from "@web/core/network";
import { listId } from "@web/model/relational_model";

/**
 * @param {Object} renderer
 * @param {Object} record
 * @param {number|string} targetId
 * @returns {Map<number|string, boolean>}
 */
export function getRecordsToRecompute(renderer, record, targetId) {
    const optionalStateMap = new Map();

    if (renderer.isSection(record)) {
        const currentIndex = renderer.props.list.records.findIndex(
            (r) => r.id === record.id,
        );
        const targetIndex = renderer.props.list.records.findIndex(
            (r) => r.id === targetId,
        );
        if (currentIndex > targetIndex) {
            for (let i = currentIndex; i > targetIndex; i--) {
                if (!renderer.props.list.records[i].data.display_type) {
                    optionalStateMap.set(
                        renderer.props.list.records[i].id,
                        renderer.shouldCollapse(
                            renderer.props.list.records[i],
                            "is_optional",
                        ),
                    );
                }
            }
            for (const sectionRecord of getSectionRecords(
                renderer.props.list,
                record,
            )) {
                if (!sectionRecord.data.display_type) {
                    optionalStateMap.set(
                        sectionRecord.id,
                        renderer.shouldCollapse(sectionRecord, "is_optional"),
                    );
                }
            }
        } else {
            for (let i = currentIndex; i <= targetIndex; i++) {
                if (renderer.isSection(renderer.props.list.records[i])) {
                    for (const sectionRecord of getSectionRecords(
                        renderer.props.list,
                        renderer.props.list.records[i],
                    )) {
                        if (
                            !optionalStateMap.has(sectionRecord.id) &&
                            !sectionRecord.data.display_type
                        ) {
                            optionalStateMap.set(
                                sectionRecord.id,
                                renderer.shouldCollapse(sectionRecord, "is_optional"),
                            );
                        }
                    }
                }

                if (
                    !optionalStateMap.has(renderer.props.list.records[i].id) &&
                    !renderer.props.list.records[i].data.display_type
                ) {
                    optionalStateMap.set(
                        renderer.props.list.records[i].id,
                        renderer.shouldCollapse(
                            renderer.props.list.records[i],
                            "is_optional",
                        ),
                    );
                }
            }
        }
    } else if (!record.data.display_type) {
        optionalStateMap.set(record.id, renderer.shouldCollapse(record, "is_optional"));
    }

    return optionalStateMap;
}

/**
 * @param {Object} renderer
 * @param {Map<number|string, boolean>} recordMap
 */
export async function handleQuantityAdjustment(renderer, recordMap) {
    const qtyField = renderer.optionalQuantityField ?? "product_uom_qty";
    const commands = [];

    for (const [recordId, wasOptional] of recordMap.entries()) {
        const record = renderer.props.list.records.find((r) => r.id === recordId);
        const isOptional = renderer.shouldCollapse(record, "is_optional");

        if (wasOptional && !isOptional && !record.data[qtyField]) {
            commands.push(
                x2ManyCommands.update(listId(record), {
                    [qtyField]: 1,
                }),
            );
        } else if (!wasOptional && isOptional) {
            commands.push(
                x2ManyCommands.update(listId(record), {
                    [qtyField]: 0,
                }),
            );
        }
    }

    await renderer.props.list.applyCommands(commands, { sort: true });
}
