import { hover, queryFirst } from "@odoo/hoot-dom";
import { runAllTimers } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { SELECTORS } from "./web_gantt_test_helpers";

/**
 * @typedef {import("@odoo/hoot-dom").Target} Target
 *
 * @typedef {import("@web_gantt/gantt_renderer").ConnectorId} ConnectorId
 * @typedef {import("@web_gantt/gantt_renderer").GanttRenderer} GanttRenderer
 * @typedef {import("@web_gantt/gantt_renderer").PillId} PillId
 */

/**
 * @param {Target} target
 * @param {"remove" | "reschedule-forward" | "reschedule-backward"} button
 */
export async function clickConnectorButton(target, button) {
    await hover(SELECTORS.connectorStroke, { root: target });
    await runAllTimers();
    let element = null;
    switch (button) {
        case "remove": {
            element = queryFirst(SELECTORS.connectorRemoveButton, { root: target });
            break;
        }
        case "reschedule-backward": {
            element = queryFirst(`${SELECTORS.connectorRescheduleButton}:first-of-type`, {
                root: target,
            });
            break;
        }
        case "reschedule-forward": {
            element = queryFirst(`${SELECTORS.connectorRescheduleButton}:last-of-type`, {
                root: target,
            });
            break;
        }
    }
    return contains(element).click();
}

/**
 * @param {ConnectorId | number | "new"} id
 */
export function getConnector(id) {
    if (typeof id !== "string" || !id.startsWith("__connector__")) {
        id = `__connector__${id}`;
    }
    return `${SELECTORS.cellContainer} ${SELECTORS.connector}[data-connector-id='${id}']`;
}

/**
 * @param {GanttRenderer} renderer
 */
export function getConnectorMap(renderer) {
    /**
     * @param {PillId} pillId
     */
    const getIdAndUserIdFromPill = (pillId) => {
        /** @type {[ResId, ResId]} */
        const result = [renderer.pills[pillId]?.record.id || false, false];
        if (result[0]) {
            const pills = renderer.mappingRecordToPillsByRow[result[0]]?.pills;
            if (pills) {
                const pillEntry = Object.entries(pills).find((e) => e[1].id === pillId);
                if (pillEntry) {
                    const [firstGroup] = JSON.parse(pillEntry[0]);
                    if (firstGroup.user_ids?.length) {
                        result[1] = firstGroup.user_ids[0] || false;
                    }
                }
            }
        }
        return result;
    };

    /** @type {Map<ConnectorTaskIds, ConnectorProps>} */
    const connectorMap = new Map();
    for (const connector of Object.values(renderer.connectors)) {
        const { sourcePillId, targetPillId } = renderer.mappingConnectorToPills[connector.id];
        if (!sourcePillId || !targetPillId) {
            continue;
        }
        const key = JSON.stringify([
            ...getIdAndUserIdFromPill(sourcePillId),
            ...getIdAndUserIdFromPill(targetPillId),
        ]);
        connectorMap.set(key, connector);
    }
    return connectorMap;
}

/**
 * @param {ConnectorId | number | "new"} id
 */
export function getConnectorStroke(id) {
    return `${getConnector(id)} ${SELECTORS.connectorStroke}`;
}
