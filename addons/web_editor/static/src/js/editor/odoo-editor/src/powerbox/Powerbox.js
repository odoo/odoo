/** @odoo-module **/
import { patienceDiff } from './patienceDiff.js';
import { getRangePosition } from '../utils/utils.js';

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
 *     groupName: string;
 *     title: string;
 *     description: string;
 *     fontawesome: string; // a fontawesome class name
 *     callback: () => void; // to execute when the command is picked
 *     isDisabled?: () => boolean; // return true to disable the command
 * }
 */

export class Powerbox {
    constructor({
        commands, commandFilters, editable, getContextFromParentRect,
        onOpen, onShow, onStop, beforeCommand, afterCommand
    } = {}) {
        this.commands = commands;
        this.commandFilters = commandFilters || [];
        this.editable = editable;
        this.getContextFromParentRect = getContextFromParentRect;
        this.onOpen = onOpen;
        this.onShow = onShow;
        this.onStop = onStop;
        this.beforeCommand = beforeCommand;
        this.afterCommand = afterCommand;
        this.isOpen = false;
        this.document = editable.ownerDocument;

        // Draw the powerbox.
        this.el = document.createElement('div');
        this.el.className = 'oe-commandbar-wrapper';
        this.el.style.display = 'none';
        document.body.append(this.el);
        this._mainWrapperElement = document.createElement('div');
        this._mainWrapperElement.className = 'oe-commandbar-mainWrapper';
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
     */
    open(commands=this.commands) {
        if (this.onOpen) {
            this.onOpen();
        }
        commands = this._getCurrentCommands(commands);
        this._context = {
            commands, filteredCommands: commands, selectedCommand: undefined,
            initialTarget: this.editable, initialValue: this.editable.textContent,
            lastText: undefined,
        }
        this.isOpen = true;
        this._render(this._context.commands);
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
     * Render the Powerbox with the given commands, grouped by `groupName`.
     *
     * @private
     * @param {PowerboxCommand[]} commands
     */
    _render(commands) {
        const parser = new DOMParser();
        this._mainWrapperElement.innerHTML = '';
        this._hoverActive = false;
        this._mainWrapperElement.classList.toggle('oe-commandbar-noResult', commands.length === 0);
        this._context.selectedCommand = commands.find(command => command === this._context.selectedCommand) || commands[0];
        for (const [groupName, groupCommands] of Object.entries(this._groupCommands(commands))) {
            const groupWrapperEl = parser.parseFromString(`
                <div class="oe-commandbar-groupWrapper">
                    <div class="oe-commandbar-groupName"></div>
                </div>`, 'text/html').body.firstChild;
            this._mainWrapperElement.append(groupWrapperEl);
            groupWrapperEl.firstElementChild.innerText = groupName;
            for (const command of groupCommands) {
                const commandElWrapper = document.createElement('div');
                commandElWrapper.className = 'oe-commandbar-commandWrapper';
                commandElWrapper.classList.toggle('active', this._context.selectedCommand === command);
                commandElWrapper.replaceChildren(...parser.parseFromString(`
                    <div class="oe-commandbar-commandLeftCol">
                        <i class="oe-commandbar-commandImg fa"></i>
                    </div>
                    <div class="oe-commandbar-commandRightCol">
                        <div class="oe-commandbar-commandTitle"></div>
                        <div class="oe-commandbar-commandDescription"></div>
                    </div>`, 'text/html').body.children);
                commandElWrapper.querySelector('.oe-commandbar-commandImg').classList.add(command.fontawesome);
                commandElWrapper.querySelector('.oe-commandbar-commandTitle').innerText = command.title;
                commandElWrapper.querySelector('.oe-commandbar-commandDescription').innerText = command.description;
                groupWrapperEl.append(commandElWrapper);
                // Handle events on command (activate and pick).
                commandElWrapper.addEventListener('mousemove', () => {
                    this.el.querySelector('.oe-commandbar-commandWrapper.active').classList.remove('active');
                    this._context.selectedCommand = command;
                    commandElWrapper.classList.add('active');
                });
                commandElWrapper.addEventListener('mousedown', ev => {
                        ev.preventDefault();
                        ev.stopImmediatePropagation();
                        this._pickCommand(command);
                    }, true,
                );
            }
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
     * Filter an array of commands based on the given term using fuzzy matching.
     *
     * @private
     * @param {PowerboxCommand[]} commands
     * @param {string} term
     * @returns {PowerboxCommand[]}
     */
    _filter(commands, term) {
        term = term.toLowerCase().replaceAll(/\s/g, '\\s').replaceAll('\u200B', '');
        if (term.length) {
            const regex = new RegExp(term.split('').map(char => char.replace(REGEX_RESERVED_CHARS, '\\$&')).join('.*'));
            return commands.filter(command => `${command.groupName} ${command.title}`.toLowerCase().match(regex));
        } else {
            return commands;
        }
    }
    /**
     * Take a list of commands, filter them based on `commandFilters` and
     * `isDisabled`) and return the remaining commands, ordered so that commands
     * that belong to the same group are grouped together.
     * Note: `commandFilters` is on the Powerbox instance and allows the
     * filtering of several commands at once (eg, a whole group), while
     * `isDisabled` is on a specific command and is made to target that command.
     *
     * @see commandFilters {Array<() => PowerboxCommand[]} return commands that can be used.
     * @see command.isDisabled {() => boolean} return true if the command is disabled.
     * @private
     * @param {PowerboxCommand[]} commands
     * @returns {PowerboxCommand[]}
     */
    _getCurrentCommands(commands) {
        /**
         * Some available commands may need to be disabled in certain
         * situations. i.e.: in a knowledge article, prevent the usage of the
         * /template command inside a /template block.
         */
        for (let filter of this.commandFilters) {
            commands = filter(commands);
        }
        // Do not show disabled commands.
        commands = commands.filter(command => !command.isDisabled || !command.isDisabled());
        return this._orderCommandsByGroup(commands);
    }
    /**
     * Takes a list of commands and returns an object whose keys are all
     * existing group names and whose values are each of these groups' commands.
     *
     * @private
     * @param {PowerboxCommand[]} commands
     * @returns {{[key: groupName]: PowerboxCommand[]}>}
     */
    _groupCommands(commands) {
        const groups = {};
        for (const command of commands) {
            groups[command.groupName] = [...(groups[command.groupName] || []), command];
        }
        return groups;
    }
    /**
     * Take a list of commands and returns them reordered so that commands that
     * belong to the same group are grouped together.
     *
     * @private
     * @param {PowerboxCommand[]} commands
     * @returns {PowerboxCommand[]}
     */
    _orderCommandsByGroup(commands) {
        const groups = this._groupCommands(commands);
        const reorderedCommands = [];
        for (const groupCommands of Object.values(groups)) {
            reorderedCommands.push(...groupCommands);
        }
        return reorderedCommands;
    }
    /**
     * Recompute the Powerbox's position base on the selection in the document.
     *
     * @private
     */
    _resetPosition() {
        const position = getRangePosition(this.el, this.document);
        if (position) {
            let { left, top } = position;
            if (this.getContextFromParentRect) {
                const parentContextRect = this.getContextFromParentRect();
                left += parentContextRect.left;
                top += parentContextRect.top;
            }
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
            this._context.lastText = diff.bMove.join('');
            if (this._context.lastText.match(/\s/)) {
                this.close();
            } else {
                this._context.filteredCommands = this._context.lastText === ''
                    ? this._context.commands
                    : this._filter(this._context.commands, this._context.lastText);
                this._render(this._context.filteredCommands);
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
            this._render(this._context.filteredCommands);
            this.el.querySelector('.oe-commandbar-commandWrapper.active').scrollIntoView({block: 'nearest', inline: 'nearest'});
        }
    }
}
