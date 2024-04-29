/** @odoo-module alias=@web/../tests/core/utils/nested_sortable_tests default=false */

import { drag, getFixture } from "@web/../tests/helpers/utils";

/**
 * Dragging methods taking into account the fact that it's the top of the
 * dragged element that triggers the moves (not the position of the cursor),
 * and the fact that during the first move, the dragged element is replaced by
 * a placeholder that does not have the same height. The moves are done with
 * the same x position to prevent triggering horizontal moves.
 * @param {string} from
 */
export const sortableDrag = async (from) => {
    const fixture = getFixture();
    const fromEl = fixture.querySelector(from);
    const fromRect = fromEl.getBoundingClientRect();
    const { drop, moveTo } = await drag(from);
    let isFirstMove = true;

    /**
     * @param {string} [targetSelector]
     */
    const moveAbove = async (targetSelector) => {
        const el = fixture.querySelector(targetSelector);
        await moveTo(el, {
            x: fromRect.x - el.getBoundingClientRect().x + fromRect.width / 2,
            y: fromRect.height / 2 + 5,
        });
        isFirstMove = false;
    };

    /**
     * @param {string} [targetSelector]
     */
    const moveUnder = async (targetSelector) => {
        const el = fixture.querySelector(targetSelector);
        const elRect = el.getBoundingClientRect();
        let firstMoveBelow = false;
        if (isFirstMove && elRect.y > fromRect.y) {
            // Need to consider that the moved element will be replaced by a
            // placeholder with a height of 5px
            firstMoveBelow = true;
        }
        await moveTo(el, {
            x: fromRect.x - elRect.x + fromRect.width / 2,
            y:
                ((firstMoveBelow ? -1 : 1) * fromRect.height) / 2 +
                elRect.height +
                (firstMoveBelow ? 4 : -1),
        });
        isFirstMove = false;
    };

    return { moveAbove, moveUnder, drop };
};
