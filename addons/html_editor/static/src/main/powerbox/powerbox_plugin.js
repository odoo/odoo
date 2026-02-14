import { Plugin } from "@html_editor/plugin";
import { reactive } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { rotate } from "@web/core/utils/arrays";
import { Powerbox } from "./powerbox";
import { withSequence } from "@html_editor/utils/resource";
import { omit, pick } from "@web/core/utils/objects";
import { baseContainerGlobalSelector } from "@html_editor/utils/base_container";
import { closestElement } from "@html_editor/utils/dom_traversal";

/** @typedef { import("@html_editor/core/selection_plugin").EditorSelection } EditorSelection */
/** @typedef { import("@html_editor/core/user_command_plugin").UserCommand } UserCommand */
/** @typedef { ReturnType<_t> } TranslatedString */

/**
 * @typedef {Object} PowerboxCategory
 * @property {string} id
 * @property {TranslatedString} name
 *
 * @typedef {Object} PowerboxItem
 * @property {string} categoryId Id of a powerbox category
 * @property {string} commandId Id of a user command to extend
 * @property {Object} [commandParams] Passed to the command's `run` function - optional
 * @property {TranslatedString} [title] Inheritable
 * @property {TranslatedString} [description] Inheritable
 * @property {string} [icon] fa-class - Inheritable
 * @property {TranslatedString[]} [keywords]
 * @property {(selection: EditorSelection) => boolean} [isAvailable] Optional and inheritable
 */

/**
 * The resulting powerbox command after deriving properties from a user command
 * (type for internal use).
 * @typedef {Object} PowerboxCommand
 * @property {string} categoryId
 * @property {string} categoryName
 * @property {string} title
 * @property {string} description
 * @property {string} icon
 * @property {Function} run
 * @property {TranslatedString[]} [keywords]
 * @property { (selection: EditorSelection) => boolean } isAvailable
 */

/**
 * @typedef { Object } PowerboxShared
 * @property { PowerboxPlugin['closePowerbox'] } closePowerbox
 * @property { PowerboxPlugin['getAvailablePowerboxCommands'] } getAvailablePowerboxCommands
 * @property { PowerboxPlugin['openPowerbox'] } openPowerbox
 * @property { PowerboxPlugin['updatePowerbox'] } updatePowerbox
 */

/** @typedef {PowerboxCategory[]} powerbox_categories */
/**
 * @typedef {import("plugins").CSSSelector[]} powerbox_blacklist_selectors
 *
 * @see UserCommand
 * @typedef {PowerboxItem[]} powerbox_items
 *
 * A powerbox item must derive from a user command (see UserCommand) specified
 * by commandId. Properties defined in a powerbox item override those from a
 * user command. Other properties are inferred from the UserCommand.
 *
 * Example:
 *
 *     resources = {
 *          user_commands: [
 *              // see {UserCommand}
 *              {
 *                  id: myCommand,
 *                  run: myCommandFunction,
 *                  title: _t("My Command"),
 *                  description: _t("My command's description"),
 *                  icon: "fa-bug",
 *              },
 *          ],
 *          powerbox_categories: [
 *              // see {PowerboxCategory}
 *              { id: "myCategory", name: _t("My Category") }
 *          ],
 *          powerbox_items: [
 *              // see {PowerboxItem}
 *              {
 *                  categoryId: "myCategory",
 *                  commandId: "myCommand",
 *                  title: _t("My Powerbox Command"), // overrides the user command's `title`
 *                  // `description` and `icon` are inferred from the user command
 *              }
 *          ],
 *     };
 */

export class PowerboxPlugin extends Plugin {
    static id = "powerbox";
    static dependencies = ["overlay", "selection", "history", "userCommand"];
    static shared = [
        "closePowerbox",
        "getAvailablePowerboxCommands",
        "openPowerbox",
        "updatePowerbox",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: {
            id: "openPowerbox",
            run: () =>
                this.openPowerbox({
                    commands: this.getAvailablePowerboxCommands(),
                    categories: this.getResource("powerbox_categories"),
                }),
        },
        powerbox_categories: [
            withSequence(10, { id: "structure", name: _t("Structure") }),
            withSequence(60, { id: "widget", name: _t("Widget") }),
            withSequence(100, { id: "modules", name: _t("Modules") }),
        ],
        power_buttons: withSequence(100, {
            commandId: "openPowerbox",
            description: _t("More options"),
            icon: "oi-ellipsis-v",
        }),
        hints: withSequence(30, {
            selector: baseContainerGlobalSelector,
            text: _t('Type "/" for commands'),
        }),
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
        this.powerboxCommands = this.makePowerboxCommands();
        this.addDomListener(this.editable.ownerDocument, "keydown", this.onKeyDown, {
            capture: true,
        });
    }

    /**
     * @returns {PowerboxCommand[]}
     */
    getAvailablePowerboxCommands() {
        const selection = this.dependencies.selection.getEditableSelection();
        const blacklistSelector = this.getResource("powerbox_blacklist_selectors").join(", ");
        if (blacklistSelector && closestElement(selection.anchorNode).matches(blacklistSelector)) {
            return [];
        }
        return this.powerboxCommands.filter((cmd) => cmd.isAvailable(selection));
    }

    /**
     * @returns {PowerboxCommand[]}
     */
    makePowerboxCommands() {
        /** @type {PowerboxItem[]} */
        const powerboxItems = this.getResource("powerbox_items");
        /** @type {PowerboxCategory[]} */
        const categories = this.getResource("powerbox_categories");
        const categoryDict = Object.fromEntries(
            categories.map((category) => [category.id, category])
        );
        return powerboxItems.map((/** @type {PowerboxItem} */ item) => {
            const command = this.dependencies.userCommand.getCommand(item.commandId);
            return {
                ...pick(command, "title", "description", "icon"),
                ...omit(item, "commandId", "commandParams"),
                categoryName: categoryDict[item.categoryId].name,
                run: (context) => command.run(item.commandParams, context),
                isAvailable: (selection) =>
                    [command.isAvailable, item.isAvailable]
                        .filter(Boolean)
                        .every((predicate) => predicate(selection)),
            };
        });
    }

    /**
     * @param {Object} params
     * @param {PowerboxCommand[]} params.commands
     * @param {PowerboxCategory[]} [params.categories]
     * @param {Function} [params.onApplyCommand=() => {}]
     * @param {Function} [params.onClose=() => {}]
     */
    openPowerbox({ commands, categories, onApplyCommand = () => {}, onClose = () => {} } = {}) {
        this.closePowerbox();
        if (!commands.length) {
            return;
        }
        this.onApplyCommand = onApplyCommand;
        this.onClose = onClose;
        this.updatePowerbox(commands, categories);
    }

    /**
     * @param {PowerboxCommand[]} commands
     * @param {PowerboxCategory[]} [categories]
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
                ev.stopImmediatePropagation();
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
                ev.stopImmediatePropagation();
                this.state.currentIndex = rotate(this.state.currentIndex, this.state.commands, -1);
                break;
            }
            case "ArrowDown": {
                ev.preventDefault();
                ev.stopImmediatePropagation();
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
        const context = {};
        this.onApplyCommand(command, context);
        command.run(context);
        this.closePowerbox();
    }
}
