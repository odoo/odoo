/* Copyright 2018 Onestein
 * License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl). */

odoo.define("web_timeline.TimelineCanvas", function (require) {
    "use strict";
    const Widget = require("web.Widget");

    /**
     * Used to draw stuff on upon the timeline view.
     */
    const TimelineCanvas = Widget.extend({
        template: "TimelineView.Canvas",

        /**
         * Clears all drawings (svg elements) from the canvas.
         */
        clear: function () {
            this.$(" > :not(defs)").remove();
        },

        /**
         * Gets the path from one point to another.
         *
         * @param {Object} rectFrom
         * @param {Object} rectTo
         * @param {Number} widthMarker The marker's width of the polyline
         * @param {Number} breakAt The space between the line turns
         * @returns {Array} Each item represents a coordinate
         */
        get_polyline_points: function (rectFrom, rectTo, widthMarker, breakAt) {
            let fromX = 0,
                toX = 0;
            if (rectFrom.x < rectTo.x + rectTo.w) {
                fromX = rectFrom.x + rectFrom.w + widthMarker;
                toX = rectTo.x;
            } else {
                fromX = rectFrom.x - widthMarker;
                toX = rectTo.x + rectTo.w;
            }
            let deltaBreak = 0;
            if (fromX < toX) {
                deltaBreak = fromX + breakAt - (toX - breakAt);
            } else {
                deltaBreak = fromX - breakAt - (toX + breakAt);
            }
            const fromHalfHeight = rectFrom.h / 2;
            const fromY = rectFrom.y + fromHalfHeight;
            const toHalfHeight = rectTo.h / 2;
            const toY = rectTo.y + toHalfHeight;
            const xDiff = fromX - toX;
            const yDiff = fromY - toY;
            const threshold = breakAt + widthMarker;
            const spaceY = toHalfHeight + 2;

            const points = [[fromX, fromY]];
            const _addPoints = (space, ePoint, mode) => {
                if (mode) {
                    points.push([fromX + breakAt, fromY]);
                    points.push([fromX + breakAt, ePoint + space]);
                    points.push([toX - breakAt, toY + space]);
                    points.push([toX - breakAt, toY]);
                } else {
                    points.push([fromX - breakAt, fromY]);
                    points.push([fromX - breakAt, ePoint + space]);
                    points.push([toX + breakAt, toY + space]);
                    points.push([toX + breakAt, toY]);
                }
            };
            if (fromY !== toY) {
                if (Math.abs(xDiff) < threshold) {
                    points.push([fromX + breakAt, toY + yDiff]);
                    points.push([fromX + breakAt, toY]);
                } else {
                    const yDiffSpace = yDiff > 0 ? spaceY : -spaceY;
                    _addPoints(yDiffSpace, toY, rectFrom.x < rectTo.x + rectTo.w);
                }
            } else if (Math.abs(deltaBreak) >= threshold) {
                _addPoints(spaceY, fromY, fromX < toX);
            }
            points.push([toX, toY]);

            return points;
        },

        /**
         * Draws an arrow.
         *
         * @param {HTMLElement} from Element to draw the arrow from
         * @param {HTMLElement} to Element to draw the arrow to
         * @param {String} color Color of the line
         * @param {Number} width Width of the line
         * @returns {HTMLElement} The created SVG polyline
         */
        draw_arrow: function (from, to, color, width) {
            return this.draw_line(from, to, color, width, "#arrowhead", 10, 12);
        },

        /**
         * Draws a line.
         *
         * @param {HTMLElement} from Element to draw the line from
         * @param {HTMLElement} to Element to draw the line to
         * @param {String} color Color of the line
         * @param {Number} width Width of the line
         * @param {String} markerStart Start marker of the line
         * @param {Number} widthMarker The marker's width of the polyline
         * @param {Number} breakLineAt The space between the line turns
         * @returns {HTMLElement} The created SVG polyline
         */
        draw_line: function (
            from,
            to,
            color,
            width,
            markerStart,
            widthMarker,
            breakLineAt
        ) {
            const $from = $(from);
            const childPosFrom = $from.offset();
            const parentPosFrom = $from.closest(".vis-center").offset();
            const rectFrom = {
                x: childPosFrom.left - parentPosFrom.left,
                y: childPosFrom.top - parentPosFrom.top,
                w: $from.width(),
                h: $from.height(),
            };
            const $to = $(to);
            const childPosTo = $to.offset();
            const parentPosTo = $to.closest(".vis-center").offset();
            const rectTo = {
                x: childPosTo.left - parentPosTo.left,
                y: childPosTo.top - parentPosTo.top,
                w: $to.width(),
                h: $to.height(),
            };
            const points = this.get_polyline_points(
                rectFrom,
                rectTo,
                widthMarker,
                breakLineAt
            );
            const line = document.createElementNS(
                "http://www.w3.org/2000/svg",
                "polyline"
            );
            line.setAttribute("points", _.flatten(points).join(","));
            line.setAttribute("stroke", color || "#000");
            line.setAttribute("stroke-width", width || 1);
            line.setAttribute("fill", "none");
            if (markerStart) {
                line.setAttribute("marker-start", "url(" + markerStart + ")");
            }
            this.$el.append(line);
            return line;
        },
    });

    return TimelineCanvas;
});
