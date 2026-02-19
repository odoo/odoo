import { Plugin } from "@html_editor/plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { closestBlock } from "@html_editor/utils/blocks";
import { isEditorTab, isEmptyBlock } from "@html_editor/utils/dom_info";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { omit, pick } from "@web/core/utils/objects";
import { debounce } from "@web/core/utils/timing";

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
        selectionchange_handlers: this.triggerDebouncedUpdatePowerButtons.bind(this),
        post_mount_component_handlers: this.updatePowerButtons.bind(this),
    };

    setup() {
        this.powerButtonsOverlay = this.dependencies.localOverlay.makeLocalOverlay(
            "oe-power-buttons-overlay"
        );
        this.createPowerButtons();
        const shouldDebounce = this.config.debouncePowerbuttons !== false;
        if (shouldDebounce) {
            this.debouncedUpdatePowerButtons = debounce(this.updatePowerButtons.bind(this), 30);
        } else {
            this.debouncedUpdatePowerButtons = this.updatePowerButtons.bind(this);
        }
    }

    createPowerButtons() {
        const composePowerButton = (/**@type {PowerButton} */ item) => {
            const command = this.dependencies.userCommand.getCommand(item.commandId);
            return {
                ...pick(command, "description", "icon", "isAvailable"),
                ...omit(item, "commandId", "commandParams"),
                run: () => command.run(item.commandParams),
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
                span.className = "d-flex align-items-center";
                span.style.height = "1em";
                btn.append(span);
            }
            btn.className = className;
            btn.title = description;
            this.addDomListener(btn, "pointerdown", (ev) => ev.preventDefault());
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
        this.powerButtonsContainer.className = `o_we_power_buttons d-flex justify-content-center invisible position-absolute`;
        this.powerButtonsContainer.append(...this.descriptionToElementMap.values());
        this.powerButtonsOverlay.append(this.powerButtonsContainer);
    }

    triggerDebouncedUpdatePowerButtons() {
        this.powerButtonsContainer.classList.add("invisible");
        this.debouncedUpdatePowerButtons();
    }

    updatePowerButtons() {
        this.powerButtonsContainer.classList.add("invisible");
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
            const direction = closestElement(element, "[dir]")?.getAttribute("dir");
            this.setPowerButtonsPosition(block, blockRect, direction);
            // Hide/show buttons based on their availability.
            for (const [{ isAvailable }, buttonElement] of this.descriptionToElementMap.entries()) {
                const shouldHide = Boolean(isAvailable && !isAvailable(editableSelection));
                buttonElement.classList.toggle("d-none", shouldHide); // 2nd arg must be a boolean
            }
            this.powerButtonsContainer.classList.remove("invisible");
            this.powerButtonsContainer.setAttribute("dir", direction);
        }
    }

    getPlaceholderWidth(block) {
        const hintText = block.getAttribute("o-we-hint-text");
        const cs = getComputedStyle(block);
        const canvas = this.canvas || (this.canvas = document.createElement("canvas"));
        const ctx = canvas.getContext("2d");
        ctx.font = cs.font;
        const width = ctx.measureText(hintText).width;
        return width;
    }

    /**
     *
     * @param {HTMLElement} block
     * @param {string} direction
     */
    setPowerButtonsPosition(block, blockRect, direction) {
        // Resetting the position of the power buttons.
        const overlayRect = this.powerButtonsOverlay.getBoundingClientRect();
        const placeholderWidth = this.getPlaceholderWidth(block);
        if (direction === "rtl") {
            this.powerButtonsContainer.style.left =
                blockRect.right - overlayRect.left - placeholderWidth - 30 + "px";
            this.powerButtonsContainer.style.transform = "translateX(-100%)";
        } else {
            this.powerButtonsContainer.style.transform = "unset";
            this.powerButtonsContainer.style.left = placeholderWidth + 30 + "px";
        }
        this.powerButtonsContainer.style.top = blockRect.top - overlayRect.top + "px";
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
