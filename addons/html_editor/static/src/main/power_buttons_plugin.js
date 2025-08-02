import { Plugin } from "@html_editor/plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { closestBlock } from "@html_editor/utils/blocks";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { omit, pick } from "@web/core/utils/objects";

/** @typedef {import("./powerbox/powerbox_plugin").PowerboxCommand} PowerboxCommand */

/**
 * @typedef {Object} PowerButton
 * @property {string} commandId
 * @property {Object} [commandParams]
 * @property {string} [description] Can be inferred from the user command
 * @property {string} [icon] Can be inferred from the user command
 * @property {string} [text] Mandatory if `icon` is not provided
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
 *              description: _t("Apply my command"),
 *              icon: "fa-bug",
 *          },
 *      ],
 *      power_buttons: [
 *          {
 *              commandId: "myCommand",
 *              commandParams: { myParam: "myValue" },
 *              description: _t("Do powerfull stuff"), // overrides the user command's `description`
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
                ...pick(command, "description", "icon"),
                ...omit(item, "commandId", "commandParams"),
                run: () => command.run(item.commandParams),
                isAvailable: (selection) =>
                    [command.isAvailable, item.isAvailable]
                        .filter(Boolean)
                        .every((predicate) => predicate(selection)),
            };
        };
        const renderButton = ({ description, icon, text, run }) => {
            const btn = this.document.createElement("button");
            let className = "power_button btn px-2 py-1 cursor-pointer";
            if (icon) {
                const iconLibrary = icon.includes("fa-") ? "fa" : "oi";
                className += ` ${iconLibrary} ${icon}`;
            } else {
                const span = this.document.createElement("span");
                span.textContent = text;
                span.className = "d-flex align-items-center text-nowrap";
                span.style.height = "1em";
                btn.append(span);
            }
            btn.className = className;
            btn.title = description;
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
        const { editableSelection, currentSelectionIsInEditable } =
            this.dependencies.selection.getSelectionData();
        if (!currentSelectionIsInEditable) {
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
            !this.services.ui.isSmall &&
            !closestElement(editableSelection.anchorNode, "td, th, li") &&
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
                const shouldHide = Boolean(!isAvailable(editableSelection));
                buttonElement.classList.toggle("d-none", shouldHide); // 2nd arg must be a boolean
            }
            this.setPowerButtonsPosition(block, blockRect, direction);
        }
    }

    getPlaceholderWidth(block) {
        let width;
        this.dependencies.history.ignoreDOMMutations(() => {
            const clone = block.cloneNode(true);
            clone.innerText = clone.getAttribute("o-we-hint-text");
            clone.style.width = "fit-content";
            clone.style.visibility = "hidden";
            this.editable.appendChild(clone);
            width = clone.getBoundingClientRect().width;
            this.editable.removeChild(clone);
        });
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
