import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { omit, pick } from "@web/core/utils/objects";

/** @typedef {import("./powerbox/powerbox_plugin").PowerboxCommand} PowerboxCommand */

/**
 * @typedef {Object} PowerButton
 * @property {string} commandId
 * @property {Object} [commandParams]
 * @property {string} [title] Can be inferred from the user command
 * @property {string} [icon] Can be inferred from the user command
 */
/**
 * A power button is added by referencing an existing user command.
 *
 * Example:
 *
 * resources = {
 *      user_commands: [
 *          {
 *              id: myCommand,
 *              run: myCommandFunction,
 *              title: _t("My Command"),
 *              icon: "fa-bug",
 *          },
 *      ],
 *      power_buttons: [
 *          {
 *              commandId: "myCommand",
 *              commandParams: { myParam: "myValue" },
 *              title: _t("My Power Button"), // overrides the user command's `title`
 *              // `icon` is derived from the user command
 *          }
 *      ],
 * };
 */

export class PowerButtonsPlugin extends Plugin {
    static id = "powerButtons";
    static dependencies = ["selection", "position", "localOverlay", "powerbox", "userCommand"];
    resources = {
        layout_geometry_change_handlers: this.updatePowerButtons.bind(this),
        selectionchange_handlers: this.updatePowerButtons.bind(this),
    };

    setup() {
        this.powerButtonsOverlay = this.dependencies.localOverlay.makeLocalOverlay(
            "oe-power-buttons-overlay"
        );
        this.createPowerButtons();
    }

    createPowerButtons() {
        /** @returns {HTMLButtonElement} */
        const itemToButton = (/**@type {PowerButton} */ item) => {
            const command = this.dependencies.userCommand.getCommand(item.commandId);
            const composedPowerButton = {
                ...pick(command, "title", "icon"),
                ...omit(item, "commandId", "commandParams"),
                run: () => command.run(item.commandParams),
            };
            const btn = this.document.createElement("button");
            btn.className = `power_button btn px-2 py-1 cursor-pointer fa ${composedPowerButton.icon}`;
            btn.title = composedPowerButton.title;
            this.addDomListener(btn, "click", () => this.applyCommand(composedPowerButton.run));
            return btn;
        };

        this.powerButtonsContainer = this.document.createElement("div");
        this.powerButtonsContainer.className = `o_we_power_buttons d-flex justify-content-center d-none`;

        /** @type {PowerButton[]} */
        const powerButtons = this.getResource("power_buttons");
        this.powerButtonsContainer.append(...powerButtons.map(itemToButton));
        this.powerButtonsOverlay.append(this.powerButtonsContainer);
    }

    updatePowerButtons() {
        this.powerButtonsContainer.classList.add("d-none");
        const { editableSelection, documentSelectionIsInEditable } =
            this.dependencies.selection.getSelectionData();
        if (!documentSelectionIsInEditable) {
            return;
        }
        const block = closestBlock(editableSelection.anchorNode);
        const element = closestElement(editableSelection.anchorNode);
        if (
            editableSelection.isCollapsed &&
            element?.tagName === "P" &&
            isEmptyBlock(block) &&
            !this.services.ui.isSmall &&
            !closestElement(editableSelection.anchorNode, "td") &&
            !block.style.textAlign &&
            this.getResource("power_buttons_visibility_predicates").every((predicate) =>
                predicate(editableSelection)
            )
        ) {
            this.powerButtonsContainer.classList.remove("d-none");
            const direction = closestElement(element, "[dir]")?.getAttribute("dir");
            this.powerButtonsContainer.setAttribute("dir", direction);
            this.setPowerButtonsPosition(block, direction);
        }
    }

    /**
     *
     * @param {HTMLElement} block
     * @param {string} direction
     */
    setPowerButtonsPosition(block, direction) {
        const overlayStyles = this.powerButtonsOverlay.style;
        // Resetting the position of the power buttons.
        overlayStyles.top = "0px";
        overlayStyles.left = "0px";
        const blockRect = block.getBoundingClientRect();
        const buttonsRect = this.powerButtonsContainer.getBoundingClientRect();
        if (direction === "rtl") {
            overlayStyles.left =
                blockRect.right -
                buttonsRect.width -
                buttonsRect.x -
                buttonsRect.width * 0.85 +
                "px";
        } else {
            overlayStyles.left = blockRect.left - buttonsRect.x + buttonsRect.width * 0.85 + "px";
        }
        overlayStyles.top = blockRect.top - buttonsRect.top + "px";
        overlayStyles.height = blockRect.height + "px";
    }

    /**
     * @param {Function} commandFn
     */
    async applyCommand(commandFn) {
        const btns = [...this.powerButtonsContainer.querySelectorAll(".btn")];
        btns.forEach((btn) => btn.classList.add("disabled"));
        await commandFn();
        btns.forEach((btn) => btn.classList.remove("disabled"));
    }
}
