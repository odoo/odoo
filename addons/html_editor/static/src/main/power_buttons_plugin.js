import { Plugin } from "@html_editor/plugin";
import { closestBlock } from "@html_editor/utils/blocks";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { _t } from "@web/core/l10n/translation";

export class PowerButtonsPlugin extends Plugin {
    static name = "power_buttons";
    static dependencies = ["selection", "local-overlay", "powerbox"];
    resources = {
        layoutGeometryChange: this.updatePowerButtons.bind(this),
        onSelectionChange: this.updatePowerButtons.bind(this),
    };

    setup() {
        this.buttons = this.getResource("powerButtons")
            .map((id) => this.getResource("powerboxItems").find((item) => item.id === id))
            .filter(Boolean);
        this.buttons.push({
            id: "more_options",
            name: _t("More options"),
            fontawesome: "fa-ellipsis-v",
            action: () => {
                this.openPowerbox();
            },
        });
        this.powerButtonsOverlay = this.shared.makeLocalOverlay("oe-power-buttons-overlay");
        this.categories = this.getResource("powerboxCategory");
        this.commands = this.getResource("powerboxItems").map((command) => ({
            ...command,
            categoryName: this.categories.find((category) => category.id === command.category).name,
        }));
        this.createPowerButtons();
    }

    createPowerButtons() {
        this.powerButtons = document.createElement("div");
        this.powerButtons.className = `o_we_power_buttons d-flex justify-content-center d-none`;
        for (const button of this.buttons) {
            const btn = document.createElement("div");
            btn.className = `power_button btn px-2 py-1 cursor-pointer fa ${button.fontawesome}`;
            btn.title = button.name;
            btn.addEventListener("click", () => this.applyCommand(button));
            this.powerButtons.appendChild(btn);
        }
        this.powerButtonsOverlay.appendChild(this.powerButtons);
    }

    updatePowerButtons() {
        this.powerButtons.classList.add("d-none");
        const { editableSelection, documentSelectionIsInEditable } = this.shared.getSelectionData();
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
            this.getResource("showPowerButtons").every((showPowerButtons) =>
                showPowerButtons(editableSelection)
            )
        ) {
            this.powerButtons.classList.remove("d-none");
            let direction = block.getAttribute("dir");
            if (block.tagName === "LI") {
                direction = block.parentElement.getAttribute("dir");
            }
            this.powerButtons.setAttribute("dir", direction);
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
        const buttonsRect = this.powerButtons.getBoundingClientRect();
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

    async applyCommand(command) {
        const btns = [...this.powerButtons.querySelectorAll(".btn")];
        btns.forEach((btn) => btn.classList.add("disabled"));
        await command.action(this.dispatch);
        btns.forEach((btn) => btn.classList.remove("disabled"));
    }

    openPowerbox() {
        const selection = this.shared.getEditableSelection();
        this.enabledCommands = this.commands.filter(
            (cmd) => !cmd.isAvailable?.(selection.anchorNode)
        );
        this.shared.openPowerbox({
            commands: this.enabledCommands,
            categories: this.categories,
        });
    }
}
