import { Plugin } from "@html_editor/plugin";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { closestBlock } from "@html_editor/utils/blocks";
import { isEditorTab, isEmptyBlock } from "@html_editor/utils/dom_info";
import { closestElement, descendants } from "@html_editor/utils/dom_traversal";
import { omit, pick } from "@web/core/utils/objects";
import { debounce } from "@web/core/utils/timing";

/** @typedef {import("./powerbox/powerbox_plugin").PowerboxCommand} PowerboxCommand */
/** @typedef {import("@html_editor/core/selection_plugin").EditorSelection} EditorSelection */

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
 * @typedef {((selection: EditorSelection) => boolean)[]} should_show_power_buttons_predicates
 */

/**
 * @typedef {{ commandId: string }[]} power_buttons
 *
 * A power button is added by referencing an existing user command.
 *
 * Example:
 *
 *     resources = {
 *          user_commands: [
 *              {
 *                  id: myCommand,
 *                  run: myCommandFunction,
 *                  description: _t("Apply my command"),
 *                  icon: "fa-bug",
 *              },
 *          ],
 *          power_buttons: [
 *              {
 *                  commandId: "myCommand",
 *                  commandParams: { myParam: "myValue" },
 *                  description: _t("Do powerfull stuff"), // overrides the user command's `description`
 *                  // `icon` is derived from the user command
 *              }
 *          ],
 *     };
 */

// Below this size, the power buttons will overlap other menus.
const MIN_WIDTH_FOR_POWER_BUTTONS = 600;

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
    /** @type {import("plugins").EditorResources} */
    resources = {
        on_layout_geometry_change_handlers: this.updatePowerButtons.bind(this),
        on_selectionchange_handlers: this.triggerDebouncedUpdatePowerButtons.bind(this),
        on_component_mounted_handlers: this.updatePowerButtons.bind(this),
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
        const { documentSelection, editableSelection, documentSelectionIsInEditable } =
            this.dependencies.selection.getSelectionData();
        if (
            !(
                documentSelectionIsInEditable &&
                this.dependencies.selection.editableDocumentHasFocus()
            )
        ) {
            return;
        }
        const block = closestBlock(documentSelection.anchorNode);
        const blockRect = block.getBoundingClientRect();
        const editableRect = this.editable.getBoundingClientRect();
        if (
            documentSelection.isCollapsed &&
            block?.matches(baseContainerGlobalSelector) &&
            editableRect.bottom > blockRect.top &&
            isEmptyBlock(block) &&
            !descendants(block).some(isEditorTab) &&
            this.editable.offsetWidth >= MIN_WIDTH_FOR_POWER_BUTTONS &&
            !closestElement(documentSelection.anchorNode, "td, th, li") &&
            !block.style.textAlign &&
            (this.checkPredicates("should_show_power_buttons_predicates", documentSelection) ??
                true)
        ) {
            const direction = closestElement(block, "[dir]")?.getAttribute("dir");
            // Hide/show buttons based on their availability.
            for (const [{ isAvailable }, buttonElement] of this.descriptionToElementMap.entries()) {
                const shouldHide = Boolean(!isAvailable(editableSelection));
                buttonElement.classList.toggle("d-none", shouldHide); // 2nd arg must be a boolean
            }
            this.setPowerButtonsPosition(block, blockRect, direction);
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
        let referenceRect = { top: 0, left: 0 };
        let frameElement;
        try {
            frameElement = this.document.defaultView.frameElement;
        } catch {
            // We don't access the frameElement if we don't have access to it.
            // (i.e. iframe origin or sandbox restriction)
        }
        if (frameElement) {
            referenceRect = frameElement.getBoundingClientRect();
        }
        const placeholderWidth = this.getPlaceholderWidth(block);
        let newButtonContainerLeft;
        const editableRect = this.editable.getBoundingClientRect();
        if (direction === "rtl") {
            newButtonContainerLeft =
                blockRect.right - (overlayRect.left - referenceRect.left) - placeholderWidth - 30;
            if (newButtonContainerLeft <= 0) {
                this.powerButtonsContainer
                    .querySelectorAll(".power_button:not(:last-child)")
                    .forEach((el) => el.classList.add("d-none"));
                newButtonContainerLeft =
                    blockRect.right -
                    (overlayRect.left - referenceRect.left) -
                    placeholderWidth -
                    30;
            }
            this.powerButtonsContainer.style.transform = "translateX(-100%)";
        } else {
            this.powerButtonsContainer.style.transform = "unset";
            newButtonContainerLeft =
                blockRect.left - (overlayRect.left - referenceRect.left) + placeholderWidth + 30;
            if (
                newButtonContainerLeft + this.powerButtonsContainer.offsetWidth >
                editableRect.right + referenceRect.left
            ) {
                this.powerButtonsContainer
                    .querySelectorAll(".power_button:not(:last-child)")
                    .forEach((el) => el.classList.add("d-none"));
            }
        }
        this.powerButtonsContainer.style.left = newButtonContainerLeft + "px";
        this.powerButtonsContainer.style.top =
            blockRect.top - (overlayRect.top - referenceRect.top) + "px";
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
