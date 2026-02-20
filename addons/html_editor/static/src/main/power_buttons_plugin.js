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
 * @typedef {((selection: EditorSelection) => boolean)[]} power_buttons_visibility_predicates
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
        this.powerButtonsContainer.className = `o_we_power_buttons d-flex justify-content-center invisible position-absolute`;
        this.powerButtonsContainer.append(...this.descriptionToElementMap.values());
        this.powerButtonsOverlay.append(this.powerButtonsContainer);
    }

    triggerDebouncedUpdatePowerButtons() {
        this.powerButtonsContainer.classList.add("invisible");
        this.debouncedUpdatePowerButtons();
    }

    updatePowerButtons() {
<<<<<<< a220fb71c036c93fa1e75d4d37127e5eda0118f9
        this.powerButtonsContainer.classList.add("d-none");
        const { documentSelection, editableSelection, currentSelectionIsInEditable } =
||||||| 8b8abb0c39064b93badd7b78ed4c37c700b46cb3
        this.powerButtonsContainer.classList.add("d-none");
        const { editableSelection, currentSelectionIsInEditable } =
=======
        this.powerButtonsContainer.classList.add("invisible");
        const { editableSelection, currentSelectionIsInEditable } =
>>>>>>> fbc19d9ad1273fef5fa8be000aba8d6011cbca95
            this.dependencies.selection.getSelectionData();
        if (!currentSelectionIsInEditable) {
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
            !this.services.ui.isSmall &&
            !closestElement(documentSelection.anchorNode, "td, th, li") &&
            !block.style.textAlign &&
            this.getResource("power_buttons_visibility_predicates").every((predicate) =>
                predicate(documentSelection)
            )
        ) {
<<<<<<< a220fb71c036c93fa1e75d4d37127e5eda0118f9
            this.powerButtonsContainer.classList.remove("d-none");
            const direction = closestElement(block, "[dir]")?.getAttribute("dir");
            this.powerButtonsContainer.setAttribute("dir", direction);
||||||| 8b8abb0c39064b93badd7b78ed4c37c700b46cb3
            this.powerButtonsContainer.classList.remove("d-none");
            const direction = closestElement(element, "[dir]")?.getAttribute("dir");
            this.powerButtonsContainer.setAttribute("dir", direction);
=======
            const direction = closestElement(element, "[dir]")?.getAttribute("dir");
            this.setPowerButtonsPosition(block, blockRect, direction);
>>>>>>> fbc19d9ad1273fef5fa8be000aba8d6011cbca95
            // Hide/show buttons based on their availability.
            for (const [{ isAvailable }, buttonElement] of this.descriptionToElementMap.entries()) {
                const shouldHide = Boolean(!isAvailable(editableSelection));
                buttonElement.classList.toggle("d-none", shouldHide); // 2nd arg must be a boolean
            }
            this.powerButtonsContainer.classList.remove("invisible");
            this.powerButtonsContainer.setAttribute("dir", direction);
        }
    }

    getPlaceholderWidth(block) {
<<<<<<< a220fb71c036c93fa1e75d4d37127e5eda0118f9
        let width;
        this.dependencies.history.ignoreDOMMutations(() => {
            const clone = block.cloneNode(true);
            clone.innerText = clone.getAttribute("o-we-hint-text");
            clone.style.width = "fit-content";
            clone.style.visibility = "hidden";
            block.after(clone);
            width = clone.getBoundingClientRect().width;
            clone.remove();
        });
||||||| 8b8abb0c39064b93badd7b78ed4c37c700b46cb3
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
=======
        const hintText = block.getAttribute("o-we-hint-text");
        const cs = getComputedStyle(block);
        const canvas = this.canvas || (this.canvas = document.createElement("canvas"));
        const ctx = canvas.getContext("2d");
        ctx.font = cs.font;
        const width = ctx.measureText(hintText).width;
>>>>>>> fbc19d9ad1273fef5fa8be000aba8d6011cbca95
        return width;
    }

    /**
     *
     * @param {HTMLElement} block
     * @param {string} direction
     */
    setPowerButtonsPosition(block, blockRect, direction) {
        // Resetting the position of the power buttons.
<<<<<<< a220fb71c036c93fa1e75d4d37127e5eda0118f9
        overlayStyles.top = "0px";
        overlayStyles.left = "0px";
        const buttonsRect = this.powerButtonsContainer.getBoundingClientRect();
        let referenceRect = { top: 0, left: 0 };
        let frameElement;
        try {
            frameElement = this.document.defaultView.frameElement;
        } catch {
            // We don't access the frameElement if we don't have access to it.
            // (i.e. iframe origin or sandbox restriction)
||||||| 8b8abb0c39064b93badd7b78ed4c37c700b46cb3
        overlayStyles.top = "0px";
        overlayStyles.left = "0px";
        const buttonsRect = this.powerButtonsContainer.getBoundingClientRect();
        const placeholderWidth = this.getPlaceholderWidth(block) + 20;
        if (direction === "rtl") {
            overlayStyles.left =
                blockRect.right - buttonsRect.width - buttonsRect.x - placeholderWidth + "px";
        } else {
            overlayStyles.left = blockRect.left - buttonsRect.x + placeholderWidth + "px";
=======
        const overlayRect = this.powerButtonsOverlay.getBoundingClientRect();
        const placeholderWidth = this.getPlaceholderWidth(block);
        if (direction === "rtl") {
            this.powerButtonsContainer.style.left =
                blockRect.right - overlayRect.left - placeholderWidth - 30 + "px";
            this.powerButtonsContainer.style.transform = "translateX(-100%)";
        } else {
            this.powerButtonsContainer.style.transform = "unset";
            this.powerButtonsContainer.style.left = placeholderWidth + 30 + "px";
>>>>>>> fbc19d9ad1273fef5fa8be000aba8d6011cbca95
        }
<<<<<<< a220fb71c036c93fa1e75d4d37127e5eda0118f9
        if (frameElement) {
            referenceRect = frameElement.getBoundingClientRect();
        }
        const placeholderWidth = this.getPlaceholderWidth(block) + 20;
        let newButtonContainerLeft;
        const editableRect = this.editable.getBoundingClientRect();
        if (direction === "rtl") {
            newButtonContainerLeft =
                blockRect.right + referenceRect.left - buttonsRect.right - placeholderWidth;
            if (newButtonContainerLeft <= 0) {
                this.powerButtonsContainer
                    .querySelectorAll(".power_button:not(:last-child)")
                    .forEach((el) => el.classList.add("d-none"));
                const buttonRect = this.powerButtonsContainer
                    .querySelector(".power_button:last-child")
                    .getBoundingClientRect();
                newButtonContainerLeft =
                    blockRect.right + referenceRect.left - buttonRect.right - placeholderWidth;
            }
        } else {
            newButtonContainerLeft =
                blockRect.left + referenceRect.left - buttonsRect.left + placeholderWidth;
            if (newButtonContainerLeft + buttonsRect.width >= editableRect.width) {
                this.powerButtonsContainer
                    .querySelectorAll(".power_button:not(:last-child)")
                    .forEach((el) => el.classList.add("d-none"));
            }
        }
        overlayStyles.left = newButtonContainerLeft + "px";
        overlayStyles.top = blockRect.top - (buttonsRect.top - referenceRect.top) + "px";
        overlayStyles.height = blockRect.height + "px";
||||||| 8b8abb0c39064b93badd7b78ed4c37c700b46cb3
        overlayStyles.top = blockRect.top - buttonsRect.top + "px";
        overlayStyles.height = blockRect.height + "px";
=======
        this.powerButtonsContainer.style.top = blockRect.top - overlayRect.top + "px";
>>>>>>> fbc19d9ad1273fef5fa8be000aba8d6011cbca95
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
