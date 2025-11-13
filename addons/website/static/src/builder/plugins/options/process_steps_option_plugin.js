import { BuilderAction } from "@html_builder/core/builder_action";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";
import { after } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { CONTAINER_WIDTH } from "@website/builder/option_sequence";
import { connectorOptionParams, ProcessStepsOption } from "./process_steps_option";
import { BaseWebsiteBackgroundOption } from "./background_option";

export class WebsiteBackgroundProcessStepOption extends BaseWebsiteBackgroundOption {
    static selector = ".s_process_step .s_process_step_number";
    static defaultProps = {
        withColors: true,
        withImages: false,
        withColorCombinations: false,
    };
}

class ProcessStepsOptionPlugin extends Plugin {
    static id = "processStepsOption";
    resources = {
        builder_options: [
            withSequence(after(CONTAINER_WIDTH), ProcessStepsOption),
            WebsiteBackgroundProcessStepOption,
        ],
        builder_actions: {
            ChangeConnectorAction,
            ChangeArrowColorAction,
        },
        // The reload of the connectors is done at the
        // 'content_updated_handlers' (each time there is a DOM mutation) and
        // not at the normalize as there are cases where we want to reload the
        // connectors even if there were no step added (e.g: a column of the
        // snippet is being resized).
        content_updated_handlers: (rootEl) =>
            applyFunDependOnSelectorAndExclude(reloadConnectors, rootEl, {
                selector: ProcessStepsOption.selector,
            }),
        dropzone_selector: {
            selector: ".s_process_step",
            dropLockWithin: ".s_process_steps",
        },
    };
}

export class ChangeConnectorAction extends ClassAction {
    static id = "changeConnector";
    apply({ editingElement, params: { mainParam: className } }) {
        super.apply(...arguments);
        reloadConnectors(editingElement);
        let markerEnd = "";
        if (
            ["s_process_steps_connector_arrow", "s_process_steps_connector_curved_arrow"].includes(
                className
            )
        ) {
            const arrowHeadEl = editingElement.querySelector(".s_process_steps_arrow_head");
            // The arrowhead id is set here so that they are different per snippet
            if (!arrowHeadEl.id) {
                arrowHeadEl.id = "s_process_steps_arrow_head" + Date.now();
            }
            markerEnd = `url(#${arrowHeadEl.id})`;
        }
        editingElement
            .querySelectorAll(".s_process_step_connector path")
            .forEach((path) => path.setAttribute("marker-end", markerEnd));
    }
}

export class ChangeArrowColorAction extends BuilderAction {
    static id = "changeArrowColor";
    apply({ editingElement, value: colorValue }) {
        const arrowHeadEl = editingElement
            .closest(".s_process_steps")
            .querySelector(".s_process_steps_arrow_head");
        arrowHeadEl.querySelector("path").style.fill = colorValue;
    }
}

registry.category("website-plugins").add(ProcessStepsOptionPlugin.id, ProcessStepsOptionPlugin);

/**
 * Width and position of the connectors should be updated when one of the
 * steps is modified.
 *
 */
function reloadConnectors(editingElement) {
    const connectorOptionClasses = connectorOptionParams.map(
        (connectorOptionParam) => connectorOptionParam.key
    );
    const type =
        connectorOptionClasses.find(
            (connectorOptionClass) =>
                connectorOptionClass && editingElement.classList.contains(connectorOptionClass)
        ) || "";
    // As the connectors are only visible in desktop, we can ignore the
    // steps that are only visible in mobile.
    const stepsEls = editingElement.querySelectorAll(
        ".s_process_step:not(.o_snippet_desktop_invisible)"
    );
    const nbBootstrapCols = 12;
    let colsInRow = 0;

    for (let i = 0; i < stepsEls.length - 1; i++) {
        const connectorEl = stepsEls[i].querySelector(".s_process_step_connector");
        const stepMainElementRect = getStepMainElementRect(stepsEls[i]);
        const nextStepMainElementRect = getStepMainElementRect(stepsEls[i + 1]);
        const stepSize = getClassSuffixedInteger(stepsEls[i], "col-lg-");
        const nextStepSize = getClassSuffixedInteger(stepsEls[i + 1], "col-lg-");
        const stepOffset = getClassSuffixedInteger(stepsEls[i], "offset-lg-");
        const nextStepOffset = getClassSuffixedInteger(stepsEls[i + 1], "offset-lg-");
        const stepPaddingTop = getClassSuffixedInteger(stepsEls[i], "pt");
        const nextStepPaddingTop = getClassSuffixedInteger(stepsEls[i + 1], "pt");
        const stepHeightDifference = stepPaddingTop - nextStepPaddingTop;
        const hCurrentStepIconHeight = stepMainElementRect.height / 2;
        const hNextStepIconHeight = nextStepMainElementRect.height / 2;

        connectorEl.style.left = `calc(50% + ${stepMainElementRect.width / 2}px + 16px)`;
        connectorEl.style.height = `${
            stepMainElementRect.height + Math.abs(stepHeightDifference)
        }px`;
        connectorEl.style.width = `calc(${
            (100 * (stepSize / 2 + nextStepOffset + nextStepSize / 2)) / stepSize
        }% - ${stepMainElementRect.width / 2}px - ${nextStepMainElementRect.width / 2}px - 32px)`;

        const marginType = stepHeightDifference < 0 ? "marginBottom" : "marginTop";
        connectorEl.style[marginType] = `${0 - Math.abs(stepHeightDifference)}px`;

        const isTheLastColOfRow =
            nbBootstrapCols < colsInRow + stepSize + stepOffset + nextStepSize + nextStepOffset;
        connectorEl.classList.toggle("d-none", isTheLastColOfRow);
        colsInRow = isTheLastColOfRow ? 0 : colsInRow + stepSize + stepOffset;
        // When we are mobile view, the connector is not visible, here we
        // display it quickly just to have its size.
        connectorEl.style.display = "block";
        const { height, width } = connectorEl.getBoundingClientRect();
        connectorEl.style.removeProperty("display");
        if (type === "s_process_steps_connector_curved_arrow" && i % 2 === 0) {
            connectorEl.style.transform = stepHeightDifference ? "unset" : "scale(1, -1)";
        } else {
            connectorEl.style.transform = "unset";
        }
        connectorEl.setAttribute("viewBox", `0 0 ${width} ${height}`);
        connectorEl
            .querySelector("path")
            .setAttribute(
                "d",
                getPath(
                    type,
                    width,
                    height,
                    stepHeightDifference,
                    hCurrentStepIconHeight,
                    hNextStepIconHeight
                )
            );
    }
}
/**
 * Returns the number suffixed to the class given in parameter.
 *
 * @param {HTMLElement} el
 * @param {String} classNamePrefix
 * @returns {Integer}
 */
function getClassSuffixedInteger(el, classNamePrefix) {
    const className = [...el.classList].find((cl) => cl.startsWith(classNamePrefix));
    return className ? parseInt(className.replace(classNamePrefix, "")) : 0;
}
/**
 * Returns the step's icon or content bounding rectangle.
 *
 * @param {HTMLElement}
 * @returns {object}
 */
function getStepMainElementRect(stepEl) {
    const iconEl = stepEl.querySelector(".s_process_step_number");
    if (iconEl) {
        return iconEl.getBoundingClientRect();
    }
    const contentEls = stepEl.querySelectorAll(".s_process_step_content > *");
    // If there is no icon, the biggest text bloc in the content container
    // will be chosen.
    if (contentEls.length) {
        const contentRects = [...contentEls].map((contentEl) => {
            const range = document.createRange();
            range.selectNodeContents(contentEl);
            return range.getBoundingClientRect();
        });
        return contentRects.reduce((previous, current) =>
            current.width > previous.width ? current : previous
        );
    }
    return {};
}
/**
 * Returns the svg path based on the type of connector.
 *
 * @param {string} type
 * @param {integer} width
 * @param {integer} height
 * @returns {string}
 */
function getPath(
    type,
    width,
    height,
    stepHeightDifference,
    hCurrentStepIconHeight,
    hNextStepIconHeight
) {
    const hHeight = height / 2;
    switch (type) {
        case "s_process_steps_connector_line": {
            const verticalPaddingFactor = Math.abs(stepHeightDifference) / 8;
            if (stepHeightDifference >= 0) {
                return `M 0 ${
                    stepHeightDifference + hCurrentStepIconHeight - verticalPaddingFactor
                } L ${width} ${hNextStepIconHeight + verticalPaddingFactor}`;
            }
            return `M 0 ${hCurrentStepIconHeight + verticalPaddingFactor} L ${width} ${
                hNextStepIconHeight - stepHeightDifference - verticalPaddingFactor
            }`;
        }
        case "s_process_steps_connector_arrow": {
            // When someone plays with the y-axis, it adds the padding in
            // multiple of 8px. so here we devide it by 8 to calculate the
            // number of padding steps has been added.
            const verticalPaddingFactor = (Math.abs(stepHeightDifference) / 8) * 1.5;
            if (stepHeightDifference >= 0) {
                return `M ${0.05 * width} ${
                    stepHeightDifference + hCurrentStepIconHeight - verticalPaddingFactor
                } L ${0.95 * width - 6} ${hNextStepIconHeight + verticalPaddingFactor}`;
            }
            return `M ${0.05 * width} ${hCurrentStepIconHeight + verticalPaddingFactor} L ${
                0.95 * width - 6
            } ${Math.abs(stepHeightDifference) + hNextStepIconHeight - verticalPaddingFactor}`;
        }
        case "s_process_steps_connector_curved_arrow": {
            if (stepHeightDifference == 0) {
                return `M ${0.05 * width} ${hHeight * 1.2} Q ${width / 2} ${hHeight * 1.8} ${
                    0.95 * width - 6
                } ${hHeight * 1.2}`;
            } else if (stepHeightDifference > 0) {
                return `M ${0.05 * width} ${stepHeightDifference + hCurrentStepIconHeight} Q ${
                    width * 0.75
                } ${height * 0.75} ${0.5 * width - 6} ${hHeight} T ${
                    0.95 * width - 6
                } ${hNextStepIconHeight}`;
            }
            return `M ${0.05 * width} ${hCurrentStepIconHeight} Q ${width * 0.75} ${
                height * 0.005
            } ${0.5 * width - 6} ${hHeight} T ${0.95 * width - 6} ${
                Math.abs(stepHeightDifference) + hNextStepIconHeight
            }`;
        }
    }
    return "";
}
