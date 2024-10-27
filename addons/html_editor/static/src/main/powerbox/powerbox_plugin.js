import { Plugin } from "@html_editor/plugin";
import { isEmptyBlock } from "@html_editor/utils/dom_info";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rotate } from "@web/core/utils/arrays";
import { Powerbox } from "./powerbox";
import { withSequence } from "@html_editor/utils/resource";

/**
 * @typedef {Object} CategoriesConfig
 * @property {string} id
 * @property {string} sequence
 *
 * @typedef {Object} Command
 * @property {string} label
 * @property {string} description
 * @property {string} categoryId
 * @property {string} icon
 * @property {string} commandId
 * @property {string} commandParams
 *
 * @typedef {Object} CommandGroup
 * @property {string} id
 * @property {string} name
 * @property {Command[]} commands
 */

/**
 * @param {SelectionData} selectionData
 */
function target(selectionData) {
    const node = selectionData.editableSelection.anchorNode;
    const el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    if (
        selectionData.documentSelectionIsInEditable &&
        (el.tagName === "DIV" || el.tagName === "P") &&
        isEmptyBlock(el)
    ) {
        return el;
    }
}

/**
 * @typedef { Object } PowerboxShared
 * @property { PowerboxPlugin['closePowerbox'] } closePowerbox
 * @property { PowerboxPlugin['getAvailablePowerboxItems'] } getAvailablePowerboxItems
 * @property { PowerboxPlugin['getPowerboxItems'] } getPowerboxItems
 * @property { PowerboxPlugin['openPowerbox'] } openPowerbox
 * @property { PowerboxPlugin['updatePowerbox'] } updatePowerbox
 */

export class PowerboxPlugin extends Plugin {
    static id = "powerbox";
    static dependencies = ["overlay", "selection", "history", "userCommand"];
    static shared = [
        "getPowerboxItems",
        "getAvailablePowerboxItems",
        "openPowerbox",
        "updatePowerbox",
        "closePowerbox",
    ];
    resources = {
        hints: {
            text: _t('Type "/" for commands'),
            target,
        },
        powerboxCategories: [
            withSequence(10, { id: "structure", name: _t("Structure") }),
            withSequence(60, { id: "widget", name: _t("Widget") }),
        ],
    };

    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.overlay = this.dependencies.overlay.createOverlay(Powerbox);

        this.state = reactive({});
        this.overlayProps = {
            document: this.document,
            close: () => this.overlay.close(),
            state: this.state,
            activateCommand: (currentIndex) => {
                this.state.currentIndex = currentIndex;
            },
            applyCommand: this.applyCommand.bind(this),
        };
        this.defaultPowerboxItems = this.makeDefaultPowerboxItems();
        this.addDomListener(this.editable.ownerDocument, "keydown", this.onKeyDown);
    }
    getPowerboxItems() {
        return this.defaultPowerboxItems;
    }
    getAvailablePowerboxItems() {
        const selection = this.dependencies.selection.getEditableSelection();
        return this.defaultPowerboxItems.filter((cmd) => !cmd.isAvailable?.(selection.anchorNode));
    }
    makeDefaultPowerboxItems() {
        const powerboxItems = this.getResource("powerboxItems");
        const userCommands = this.dependencies.userCommand.getCommands();
        const categories = this.getResource("powerboxCategories");
        const categoryDict = Object.fromEntries(
            categories.map((category) => [category.id, category])
        );
        return powerboxItems.map((item) => {
            const userCommand = userCommands[item.commandId];
            return {
                ...userCommand,
                ...item,
                categoryName: categoryDict[item.categoryId].name,
                run: () => this.dependencies.userCommand.run(item.commandId, item.commandParams),
            };
        });
    }

    /**
     * @param {Command[]} commands
     */
    openPowerbox({ commands, categories, onApplyCommand = () => {}, onClose = () => {} } = {}) {
        this.closePowerbox();
        this.onApplyCommand = onApplyCommand;
        this.onClose = onClose;
        this.updatePowerbox(commands, categories);
    }

    /**
     * @param {Command[]} commands
     * @param {Category[]?} categories
     */
    updatePowerbox(commands, categories) {
        if (categories) {
            const orderCommands = [];
            for (const category of categories) {
                orderCommands.push(
                    ...commands.filter((command) => command.categoryId === category.id)
                );
            }
            commands = orderCommands;
        }
        Object.assign(this.state, {
            showCategories: !!categories,
            commands,
            currentIndex: 0,
        });
        this.overlay.open({ props: this.overlayProps });
    }

    closePowerbox() {
        if (!this.overlay.isOpen) {
            return;
        }
        this.onClose();
        this.overlay.close();
    }

    onKeyDown(ev) {
        if (!this.overlay.isOpen) {
            return;
        }
        const key = ev.key;
        switch (key) {
            case "Escape":
                this.closePowerbox();
                break;
            case "Enter":
            case "Tab":
                ev.preventDefault();
                ev.stopImmediatePropagation();
                this.applyCommand(this.state.commands[this.state.currentIndex]);
                break;
            case "ArrowUp": {
                ev.preventDefault();
                this.state.currentIndex = rotate(this.state.currentIndex, this.state.commands, -1);
                break;
            }
            case "ArrowDown": {
                ev.preventDefault();
                this.state.currentIndex = rotate(this.state.currentIndex, this.state.commands, 1);
                break;
            }
            case "ArrowLeft":
            case "ArrowRight": {
                this.closePowerbox();
                break;
            }
        }
    }

    applyCommand(command) {
        this.onApplyCommand(command);
        command.run();
        this.closePowerbox();
    }
}
