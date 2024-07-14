/** @odoo-module **/

import { Component, onWillRender, useEffect, useRef } from "@odoo/owl";

/**
 * @typedef {"error" | "warning"} ConnectorAlert
 * @typedef {`__connector__${number | "new"}`} ConnectorId
 * @typedef {import("./gantt_renderer").Point} Point
 *
 * @typedef ConnectorProps
 * @property {ConnectorId} id
 * @property {ConnectorAlert | null} alert
 * @property {boolean} highlighted
 * @property {boolean} displayButtons
 * @property {Point | () => Point | null} sourcePoint
 * @property {Point | () => Point | null} targetPoint
 *
 * @typedef {Object} PathInfo
 * @property {Point} sourceControlPoint
 * @property {Point} targetControlPoint
 * @property {Point} removeButtonPosition
 *
 * @typedef Point
 * @property {number} [x]
 * @property {number} [y]
 */

/**
 * Gets the stroke's rgba css string corresponding to the provided parameters for both the stroke and its
 * hovered state.
 *
 * @param {number} r [0, 255]
 * @param {number} g [0, 255]
 * @param {number} b [0, 255]
 * @return {{ stroke: string, hoveredStroke: string }} the css colors.
 */
export function getStrokeAndHoveredStrokeColor(r, g, b) {
    return {
        color: `rgba(${r},${g},${b},0.5)`,
        highlightedColor: `rgba(${r},${g},${b},1)`,
    };
}

export const COLORS = {
    default: getStrokeAndHoveredStrokeColor(143, 143, 143),
    error: getStrokeAndHoveredStrokeColor(211, 65, 59),
    warning: getStrokeAndHoveredStrokeColor(236, 151, 31),
    outline: getStrokeAndHoveredStrokeColor(255, 255, 255),
};

/** @extends {Component<{ reactive: ConnectorProps }, any>} */
export class GanttConnector extends Component {
    static props = {
        reactive: {
            type: Object,
            shape: {
                id: String,
                alert: {
                    type: [{ value: "error" }, { value: "warning" }, { value: null }],
                    optional: true,
                },
                highlighted: { type: Boolean, optional: true },
                displayButtons: { type: Boolean, optional: true },
                sourcePoint: [
                    { value: null },
                    Function,
                    { type: Object, shape: { left: Number, top: Number } },
                ],
                targetPoint: [
                    { value: null },
                    Function,
                    { type: Object, shape: { left: Number, top: Number } },
                ],
            },
        },
        onLeftButtonClick: { type: Function, optional: true },
        onRemoveButtonClick: { type: Function, optional: true },
        onRightButtonClick: { type: Function, optional: true },
    };
    static defaultProps = {
        highlighted: false,
        displayButtons: false,
    };
    static template = "web_gantt.GanttConnector";

    rootRef = useRef("root");
    style = {
        hoverEaseWidth: 10,
        slackness: 0.9,
        stroke: { width: 2 },
        outlineStroke: { width: 1 },
    };

    get alert() {
        return this.props.reactive.alert;
    }

    get displayButtons() {
        return this.props.reactive.displayButtons;
    }

    get highlighted() {
        return this.props.reactive.highlighted;
    }

    get id() {
        return this.props.reactive.id;
    }

    get isNew() {
        return this.id.endsWith("new");
    }

    get sourcePoint() {
        return this.props.reactive.sourcePoint;
    }

    get targetPoint() {
        return this.props.reactive.targetPoint;
    }

    setup() {
        onWillRender(this.onWillRender);

        useEffect(
            (el, sourceLeft, sourceTop, targetLeft, targetTop) => {
                if (!el) {
                    return;
                }
                const { sourceControlPoint, targetControlPoint, removeButtonPosition } =
                    this.getPathInfo(
                        { left: sourceLeft, top: sourceTop },
                        { left: targetLeft, top: targetTop },
                        this.style.slackness
                    );

                const drawingCommands = [
                    `M`,
                    `${sourceLeft},${sourceTop}`,
                    `C`,
                    `${sourceControlPoint.left},${sourceControlPoint.top}`,
                    `${targetControlPoint.left},${targetControlPoint.top}`,
                    `${targetLeft},${targetTop}`,
                ].join(" ");

                const paths = el.querySelectorAll(
                    ".o_connector_stroke, .o_connector_stroke_hover_ease"
                );
                for (const path of paths) {
                    path.setAttribute("d", drawingCommands);
                }

                const svgButtons = el.querySelector(".o_connector_stroke_buttons");
                if (svgButtons) {
                    svgButtons.setAttribute("x", removeButtonPosition.left - 24);
                    svgButtons.setAttribute("y", removeButtonPosition.top - 8);
                }
            },
            () => this.getEffectDependencies()
        );
    }

    /**
     * Refreshes the connector properties from the props.
     *
     * @param {ConnectorProps} props
     */
    computeStyle({ alert, highlighted }) {
        const key = highlighted ? "highlightedColor" : "color";
        const strokeType = alert || "default";
        this.style = {
            hoverEaseWidth: 10,
            slackness: 0.9,
            stroke: {
                color: COLORS[strokeType][key],
                width: 2,
            },
            outlineStroke: {
                color: COLORS.outline[key],
                width: 1,
            },
        };
    }

    getEffectDependencies() {
        let sourcePoint = this.sourcePoint || { left: 0, top: 0 };
        if (typeof sourcePoint === "function") {
            sourcePoint = sourcePoint();
        }
        let targetPoint = this.targetPoint || { left: 0, top: 0 };
        if (typeof targetPoint === "function") {
            targetPoint = targetPoint();
        }
        const { x, y } = this.rootRef.el?.getBoundingClientRect() || { x: 0, y: 0 };

        return [
            this.rootRef.el,
            sourcePoint.left - x,
            sourcePoint.top - y,
            targetPoint.left - x,
            targetPoint.top - y,
            this.displayButtons,
        ];
    }

    /**
     * Returns the linear interpolation for a point to be found somewhere on the line startingPoint, endingPoint.
     *
     * @param {Point} startingPoint
     * @param {Point} endingPoint
     * @param {number} lambda
     * @returns {Point}
     */
    getLinearInterpolation(startingPoint, endingPoint, lambda = 0.5) {
        return {
            left: lambda * startingPoint.left + (1 - lambda) * endingPoint.left,
            top: lambda * startingPoint.top + (1 - lambda) * endingPoint.top,
        };
    }

    /**
     * Returns the parameters of both the single Bezier curve as well as is decomposition into two beziers curves
     * (which allows to get the middle position of the single Bezier curve) for the provided source, target and
     * slackness (0 being a straight line).
     *
     * @param {Point} sourcePoint
     * @param {Point} targetPoint
     * @param {number} slackness [0, 1]
     * @returns {PathInfo}
     */
    getPathInfo(sourcePoint, targetPoint, slackness) {
        // If the source is on the left of the target, we need to invert the control points.
        const xDelta = targetPoint.left - sourcePoint.left;
        const yDelta = targetPoint.top - sourcePoint.top;
        const directionFactor = Math.sign(xDelta);

        // What follows can be seen as magic numbers. And those are indeed such numbers as they have been determined
        // by observing their shape while creating short and long connectors. These seems to allow keeping the same
        // kind of shape amongst short and long connectors.
        const xInc = 100 + (Math.abs(xDelta) * slackness) / 10;
        const yInc =
            Math.abs(yDelta) < 16 && directionFactor === -1 ? 15 - 0.001 * xDelta * slackness : 0;

        const b = {
            left: sourcePoint.left + xInc,
            top: sourcePoint.top + yInc,
        };

        // Prevent having the air pin effect when in creation and having target on the left of the source
        const c = {
            left: targetPoint.left + (this.isNew && directionFactor === -1 ? xInc : -xInc),
            top: targetPoint.top + yInc,
        };

        const e = this.getLinearInterpolation(sourcePoint, b);
        const f = this.getLinearInterpolation(b, c);
        const g = this.getLinearInterpolation(c, targetPoint);
        const h = this.getLinearInterpolation(e, f);
        const i = this.getLinearInterpolation(f, g);
        const j = this.getLinearInterpolation(h, i);

        return {
            sourceControlPoint: b,
            targetControlPoint: c,
            removeButtonPosition: j,
        };
    }

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    onLeftButtonClick() {
        if (this.props.onLeftButtonClick) {
            this.props.onLeftButtonClick();
        }
    }

    onRemoveButtonClick() {
        if (this.props.onRemoveButtonClick) {
            this.props.onRemoveButtonClick();
        }
    }

    onRightButtonClick() {
        if (this.props.onRightButtonClick) {
            this.props.onRightButtonClick();
        }
    }

    onWillRender() {
        const key = this.highlighted ? "highlightedColor" : "color";
        this.style.stroke.color = COLORS[this.alert || "default"][key];
        this.style.outlineStroke.color = COLORS.outline[key];
    }
}
