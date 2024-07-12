import { Plugin } from "@html_editor/plugin";
import { isEmpty } from "@html_editor/utils/dom_info";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rotate } from "@web/core/utils/arrays";
import { Powerbox } from "./powerbox";

/**
 * @typedef {Object} CategoriesConfig
 * @property {string} id
 * @property {string} sequence
 *
 * @typedef {Object} Command
 * @property {string} name
 * @property {string} description
 * @property {string} category
 * @property {string} fontawesome
 * @property {Function} action
 *
 * @typedef {Object} CommandGroup
 * @property {string} id
 * @property {string} name
 * @property {Command[]} commands
 */

function target(selection) {
    const node = selection.anchorNode;
    const el = node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement;
    if (selection.inEditable && (el.tagName === "DIV" || el.tagName === "P") && isEmpty(el)) {
        return el;
    }
}

export class PowerboxPlugin extends Plugin {
    static name = "powerbox";
    static dependencies = ["overlay", "selection", "history"];
    static shared = ["openPowerbox", "updatePowerbox", "closePowerbox"];
    static resources = () => ({
        temp_hints: {
            text: _t('Type "/" for commands'),
            target,
        },
        powerboxCategory: [
            { id: "structure", name: _t("Structure"), sequence: 10 },
            { id: "widget", name: _t("Widget"), sequence: 60 },
        ],
    });

    setup() {
        /** @type {import("@html_editor/core/overlay_plugin").Overlay} */
        this.overlay = this.shared.createOverlay(Powerbox, {
            position: "bottom-start",
            onClose: () => this.onClose?.(),
        });

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

        this.addDomListener(this.editable, "keydown", this.onKeyDown);
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
                    ...commands.filter((command) => command.category === category.id)
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
        command.action(this.dispatch);
        this.closePowerbox();
    }
}
