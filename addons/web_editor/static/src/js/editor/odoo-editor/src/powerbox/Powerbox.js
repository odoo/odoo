/** @odoo-module **/
import { patienceDiff } from './patienceDiff.js';
import { closestBlock, getRangePosition } from '../utils/utils.js';

const REGEX_RESERVED_CHARS = /[\\^$.*+?()[\]{}|]/g;
/**
 * Make `num` cycle from 0 to `max`.
 */
function cycle(num, max) {
    const y = max + 1;
    return ((num % y) + y) % y;
}

/**
 * interface PowerboxCommand {
 *     category: string;
 *     name: string;
 *     priority: number;
 *     description: string;
 *     fontawesome: string; // a fontawesome class name
 *     callback: () => void; // to execute when the command is picked
 *     isDisabled?: () => boolean; // return true to disable the command
 * }
 */

export class Powerbox {
    constructor({
        categories, commands, commandFilters, editable, getContextFromParentRect,
        onShow, onStop, beforeCommand, afterCommand
    } = {}) {
        this.categories = categories;
        this.commands = commands;
        this.commandFilters = commandFilters || [];
        this.editable = editable;
        this.getContextFromParentRect = getContextFromParentRect;
        this.onShow = onShow;
        this.onStop = onStop;
        this.beforeCommand = beforeCommand;
        this.afterCommand = afterCommand;
        this.isOpen = false;
        this.document = editable.ownerDocument;

        // Draw the powerbox.
        this.el = document.createElement('div');
        this.el.className = 'oe-powerbox-wrapper';
        this.el.style.display = 'none';
        document.body.append(this.el);
        this._mainWrapperElement = document.createElement('div');
        this._mainWrapperElement.className = 'oe-powerbox-mainWrapper';
        this.el.append(this._mainWrapperElement);
        this.el.addEventListener('mousedown', ev => ev.stopPropagation());

        // Set up events for later binding.
        this._boundOnKeyup = this._onKeyup.bind(this);
        this._boundOnKeydown = this._onKeydown.bind(this);
        this._boundClose = this.close.bind(this);
        this._events = [
            [this.document, 'keyup', this._boundOnKeyup],
            [this.document, 'keydown', this._boundOnKeydown, true],
            [this.document, 'mousedown', this._boundClose],
        ]
        // If the global document is different from the provided
        // options.document, which happens when the editor is inside an iframe,
        // we need to listen to the mouse event on both documents to be sure the
        // Powerbox will always close when clicking outside of it.
        if (document !== this.document) {
            this._events.push(
                [document, 'mousedown', this._boundClose],
            );
        }

    }
    destroy() {
        if (this.isOpen) {
            this.close();
        }
        this.el.remove();
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * Open the Powerbox with the given commands or with all instance commands.
     *
     * @param {PowerboxCommand[]} [commands=this.commands]
     * @param {Array<{name: string, priority: number}} [categories=this.categories]
     */
    open(commands=this.commands, categories=this.categories) {
        commands = (commands || []).map(command => ({
            ...command,
            category: command.category || '',
            name: command.name || '',
            priority: command.priority || 0,
            description: command.description || '',
            callback: command.callback || (() => {}),
        }));
        categories = (categories || []).map(category => ({
            name: category.name || '',
            priority: category.priority || 0,
        }));
        const order = (a, b) => b.priority - a.priority || a.name.localeCompare(b.name);
        // Remove duplicate category names, keeping only last declared version,
        // and order them.
        categories = [...categories].reverse().filter((category, index, cats) => (
            cats.findIndex(cat => cat.name === category.name) === index
        )).sort(order);

        // Apply optional filters to disable commands, then order them.
        for (let filter of this.commandFilters) {
            commands = filter(commands);
        }
        commands = commands.filter(command => !command.isDisabled || !command.isDisabled()).sort(order);
        commands = this._groupCommands(commands, categories).flatMap(group => group[1]);

        const selection = this.document.getSelection();
        const currentBlock = (selection && closestBlock(selection.anchorNode)) || this.editable;
        this._context = {
            commands, categories, filteredCommands: commands, selectedCommand: undefined,
            initialTarget: currentBlock, initialValue: currentBlock.textContent,
            lastText: undefined,
        }
        this.isOpen = true;
        this._render(this._context.commands, this._context.categories);
        this._bindEvents();
        this.show();
    }
    /**
     * Close the Powerbox without destroying it. Unbind events, reset context
     * and call the optional `onStop` hook.
     */
    close() {
        this.isOpen = false;
        this.hide();
        this._context = undefined;
        this._unbindEvents();
        this.onStop && this.onStop();
    };
    /**
     * Show the Powerbox and position it. Call the optional `onShow` hook.
     */
    show() {
        this.onShow && this.onShow();
        this.el.style.display = 'flex';
        this._resetPosition();
    }
    /**
     * Hide the Powerbox. If the Powerbox is active, close it.
     *
     * @see close
     */
    hide() {
        this.el.style.display = 'none';
        if (this.isOpen) {
            this.close();
        }
    }

    // -------------------------------------------------------------------------
    // Private
    // -------------------------------------------------------------------------

    /**
     * Render the Powerbox with the given commands, grouped by `category`.
     *
     * @private
     * @param {PowerboxCommand[]} commands
     * @param {Array<{name: string, priority: number}} categories
     */
    _render(commands, categories) {
        const parser = new DOMParser();
        this._mainWrapperElement.innerHTML = '';
        this._hoverActive = false;
        this._mainWrapperElement.classList.toggle('oe-powerbox-noResult', commands.length === 0);
        this._context.selectedCommand = commands.find(command => command === this._context.selectedCommand) || commands[0];
        for (const [category, categoryCommands] of this._groupCommands(commands, categories)) {
            const categoryWrapperEl = parser.parseFromString(`
                <div class="oe-powerbox-categoryWrapper">
                    <div class="oe-powerbox-category"></div>
                </div>`, 'text/html').body.firstChild;
            this._mainWrapperElement.append(categoryWrapperEl);
            categoryWrapperEl.firstElementChild.innerText = category;
            for (const command of categoryCommands) {
                const commandElWrapper = document.createElement('div');
                commandElWrapper.className = 'oe-powerbox-commandWrapper';
                commandElWrapper.classList.toggle('active', this._context.selectedCommand === command);
                commandElWrapper.replaceChildren(...parser.parseFromString(`
                    <div class="oe-powerbox-commandLeftCol">
                        <i class="oe-powerbox-commandImg fa"></i>
                    </div>
                    <div class="oe-powerbox-commandRightCol">
                        <div class="oe-powerbox-commandName"></div>
                        <div class="oe-powerbox-commandDescription"></div>
                    </div>`, 'text/html').body.children);
                commandElWrapper.querySelector('.oe-powerbox-commandImg').classList.add(command.fontawesome);
                commandElWrapper.querySelector('.oe-powerbox-commandName').innerText = command.name;
                commandElWrapper.querySelector('.oe-powerbox-commandDescription').innerText = command.description;
                categoryWrapperEl.append(commandElWrapper);
                // Handle events on command (activate and pick).
                commandElWrapper.addEventListener('mousemove', () => {
                    this.el.querySelector('.oe-powerbox-commandWrapper.active').classList.remove('active');
                    this._context.selectedCommand = command;
                    commandElWrapper.classList.add('active');
                });
                commandElWrapper.addEventListener('click', ev => {
                        ev.preventDefault();
                        ev.stopImmediatePropagation();
                        this._pickCommand(command);
                    }, true,
                );
            }
        }
        // Hide category name if there is only a single one.
        if (this._mainWrapperElement.childElementCount === 1) {
            this._mainWrapperElement.querySelector('.oe-powerbox-category').style.display = 'none';
        }
        this._resetPosition();
    }
    /**
     * Handle the selection of a command: call the command's callback. Also call
     * the `beforeCommand` and `afterCommand` hooks if they exists.
     *
     * @private
     * @param {PowerboxCommand} [command=this._context.selectedCommand]
     */
    async _pickCommand(command=this._context.selectedCommand) {
        if (command) {
            if (this.beforeCommand) {
                await this.beforeCommand();
            }
            await command.callback();
            if (this.afterCommand) {
                await this.afterCommand();
            }
        }
        this.close();
    };
    /**
     * Takes a list of commands and returns an object whose keys are all
     * existing category names and whose values are each of these categories'
     * commands. Categories with no commands are removed.
     *
     * @private
     * @param {PowerboxCommand[]} commands
     * @param {Array<{name: string, priority: number}} categories
     * @returns {{Array<[string, PowerboxCommand[]]>}>}
     */
    _groupCommands(commands, categories) {
        const groups = [];
        for (const category of categories) {
            const categoryCommands = commands.filter(command => command.category === category.name);
            commands = commands.filter(command => command.category !== category.name);
            groups.push([category.name, categoryCommands]);
        }
        // If commands remain, it means they declared categories that didn't
        // exist. Add these categories alphabetically at the end of the list.
        const remainingCategories = [...new Set(commands.map(command => command.category))];
        for (const categoryName of remainingCategories.sort((a, b) => a.localeCompare(b))) {
            const categoryCommands = commands.filter(command => command.category === categoryName);
            groups.push([categoryName, categoryCommands]);
        }
        return groups.filter(group => group[1].length);
    }
    /**
     * Take an array of commands or categories and return a reordered copy of
     * it, based on their respective priorities.
     *
     * @param {PowerboxCommand[] | Array<{name: string, priority: number}} commandsOrCategories
     * @returns {PowerboxCommand[] | Array<{name: string, priority: number}}
     */
    _orderByPriority(commandsOrCategories) {
        return [...commandsOrCategories].sort((a, b) => b.priority - a.priority || a.name.localeCompare(b.name));
    }
    /**
     * Recompute the Powerbox's position base on the selection in the document.
     *
     * @private
     */
    _resetPosition() {
        const position = getRangePosition(this.el, this.document, { getContextFromParentRect: this.getContextFromParentRect });
        if (position) {
            let { left, top } = position;
            this.el.style.left = `${left}px`;
            this.el.style.top = `${top}px`;
        } else {
            this.hide();
        }
    }
    /**
     * Add all events to their given target, based on @see _events.
     *
     * @private
     */
    _bindEvents() {
        for (const [target, eventName, callback, option] of this._events) {
            target.addEventListener(eventName, callback, option);
        }
    }
    /**
     * Remove all events from their given target, based on @see _events.
     *
     * @private
     */
    _unbindEvents() {
        for (const [target, eventName, callback, option] of this._events) {
            target.removeEventListener(eventName, callback, option);
        }
    }

    // -------------------------------------------------------------------------
    // Handlers
    // -------------------------------------------------------------------------

    /**
     * Handle keyup events to filter commands based on what was typed, and
     * prevent changing selection when using the arrow keys.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeyup(ev) {
        if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
            ev.preventDefault();
        } else {
            const diff = patienceDiff(
                this._context.initialValue.split(''),
                this._context.initialTarget.textContent.split(''),
                true,
            );
            this._context.lastText = diff.bMove.join('').replaceAll('\ufeff', '');
            const selection = this.document.getSelection();
            if (
                this._context.lastText.match(/\s/) ||
                !selection ||
                this._context.initialTarget !== closestBlock(selection.anchorNode)
            ) {
                this.close();
            } else {
                const term = this._context.lastText.toLowerCase()
                    .replaceAll(/\s/g, '\\s')
                    .replaceAll('\u200B', '')
                    .replace(REGEX_RESERVED_CHARS, '\\$&');
                if (term.length) {
                    const exactRegex = new RegExp(term, 'i');
                    const fuzzyRegex = new RegExp(term.match(/\\.|./g).join('.*'), 'i');
                    this._context.filteredCommands = this._context.commands.filter(command => {
                        const commandText = (command.category + ' ' + command.name);
                        const commandDescription = command.description.replace(/\s/g, '');
                        return commandText.match(fuzzyRegex) || commandDescription.match(exactRegex);
                    });
                } else {
                    this._context.filteredCommands = this._context.commands;
                }
                this._render(this._context.filteredCommands, this._context.categories);
            }
        }
    }
    /**
     * Handle keydown events to add keyboard interactions with the Powerbox.
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        if (ev.key === 'Enter') {
            ev.stopImmediatePropagation();
            this._pickCommand();
            ev.preventDefault();
        } else if (ev.key === 'Escape') {
            ev.stopImmediatePropagation();
            this.close();
            ev.preventDefault();
        } else if (ev.key === 'Backspace' && !this._context.lastText) {
            this.close();
        } else if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
            ev.preventDefault();
            ev.stopImmediatePropagation();

            const commandIndex = this._context.filteredCommands.findIndex(
                command => command === this._context.selectedCommand,
            );
            if (this._context.filteredCommands.length && commandIndex !== -1) {
                const nextIndex = commandIndex + (ev.key === 'ArrowDown' ? 1 : -1);
                const newIndex = cycle(nextIndex, this._context.filteredCommands.length - 1);
                this._context.selectedCommand = this._context.filteredCommands[newIndex];
            } else {
                this._context.selectedCommand = undefined;
            }
            this._render(this._context.filteredCommands, this._context.categories);
            const activeCommand = this.el.querySelector('.oe-powerbox-commandWrapper.active');
            if (activeCommand) {
                activeCommand.scrollIntoView({block: 'nearest', inline: 'nearest'});
            }
        }
    }
}
