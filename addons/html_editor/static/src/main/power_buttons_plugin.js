import { Plugin } from "@html_editor/plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { closestBlock } from "@html_editor/utils/blocks";
import { isEditorTab, isEmptyBlock } from "@html_editor/utils/dom_info";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { omit, pick } from "@web/core/utils/objects";

/** @typedef {import("./powerbox/powerbox_plugin").PowerboxCommand} PowerboxCommand */

/**
 * @typedef {Object} PowerButton
 * @property {string} commandId
 * @property {Object} [commandParams]
 * @property {string} [title] Can be inferred from the user command
 * @property {string} [icon] Can be inferred from the user command
 * @property {string} [isAvailable] Can be inferred from the user command
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
    static dependencies = [
        "baseContainer",
        "selection",
        "position",
        "localOverlay",
        "powerbox",
        "userCommand",
        "history",
    ];
    resources = {
        layout_geometry_change_handlers: this.updatePowerButtons.bind(this),
        selectionchange_handlers: this.updatePowerButtons.bind(this),
        post_mount_component_handlers: this.updatePowerButtons.bind(this),
    };

    setup() {
        this.powerButtonsOverlay = this.dependencies.localOverlay.makeLocalOverlay(
            "oe-power-buttons-overlay"
        );
        this.createPowerButtons();
    }

    createPowerButtons() {
        const composePowerButton = (/**@type {PowerButton} */ item) => {
            const command = this.dependencies.userCommand.getCommand(item.commandId);
            return {
                ...pick(command, "title", "icon", "isAvailable"),
                ...omit(item, "commandId", "commandParams"),
                run: () => command.run(item.commandParams),
            };
        };
        const renderButton = ({ title, icon, run }) => {
            const btn = this.document.createElement("button");
            btn.className = `power_button btn px-2 py-1 cursor-pointer fa ${icon}`;
            btn.title = title;
            this.addDomListener(btn, "click", () => this.applyCommand(run));
            return btn;
        };

        /** @type {PowerButton[]} */
        const powerButtonsDefinitions = this.getResource("power_buttons");
        // Merge properties from power_button and user_command.
        const powerButtons = powerButtonsDefinitions.map(composePowerButton);
        // Render HTML buttons.
        this.descriptionToElementMap = new Map(powerButtons.map((pb) => [pb, renderButton(pb)]));

        this.powerButtonsContainer = this.document.createElement("div");
        this.powerButtonsContainer.className = `o_we_power_buttons d-flex justify-content-center d-none`;
        this.powerButtonsContainer.append(...this.descriptionToElementMap.values());
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
        const blockRect = block.getBoundingClientRect();
        const editableRect = this.editable.getBoundingClientRect();
        if (
            editableSelection.isCollapsed &&
            block?.matches(baseContainerGlobalSelector) &&
            editableRect.bottom > blockRect.top &&
            isEmptyBlock(block) &&
            !descendants(block).some(isEditorTab) &&
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
            // Hide/show buttons based on their availability.
            for (const [{ isAvailable }, buttonElement] of this.descriptionToElementMap.entries()) {
                const shouldHide = Boolean(isAvailable && !isAvailable(editableSelection));
                buttonElement.classList.toggle("d-none", shouldHide); // 2nd arg must be a boolean
            }
            this.setPowerButtonsPosition(block, blockRect, direction);
        }
    }

    getPlaceholderWidth(block) {
        this.dependencies.history.disableObserver();
        const clone = block.cloneNode(true);
        clone.innerText = clone.getAttribute("placeholder");
        clone.style.width = "fit-content";
        clone.style.visibility = "hidden";
        this.editable.appendChild(clone);
        const { width } = clone.getBoundingClientRect();
        this.editable.removeChild(clone);
        this.dependencies.history.enableObserver();
        return width;
    }

    /**
     *
     * @param {HTMLElement} block
     * @param {string} direction
     */
    setPowerButtonsPosition(block, blockRect, direction) {
        const overlayStyles = this.powerButtonsOverlay.style;
        // Resetting the position of the power buttons.
        overlayStyles.top = "0px";
        overlayStyles.left = "0px";
        const buttonsRect = this.powerButtonsContainer.getBoundingClientRect();
        const placeholderWidth = this.getPlaceholderWidth(block) + 20;
        if (direction === "rtl") {
            overlayStyles.left =
                blockRect.right - buttonsRect.width - buttonsRect.x - placeholderWidth + "px";
        } else {
            overlayStyles.left = blockRect.left - buttonsRect.x + placeholderWidth + "px";
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
