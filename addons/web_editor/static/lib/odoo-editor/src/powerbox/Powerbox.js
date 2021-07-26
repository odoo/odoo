/** @odoo-module **/
import { patienceDiff } from './patienceDiff.js';
import { getRangePosition } from '../utils/utils.js';

/**
 * Make `num` cycle from 0 to `max`.
 */
function cycle(num, max) {
    const y = max + 1;
    return ((num % y) + y) % y;
}

export class Powerbox {
    constructor(options = {}) {
        this.options = options;
        this.options.width = this.options.width || 340;
        if (!this.options._t) this.options._t = string => string;

        this.el = document.createElement('div');
        this.el.className = 'oe-commandbar-wrapper';
        this.el.style.display = 'none';
        this.el.style.width = `${this.options.width}px`;
        document.body.append(this.el);

        this.options.editable.addEventListener('keydown', this.onKeydown.bind(this), true);

        this._mainWrapperElement = document.createElement('div');
        this._mainWrapperElement.className = 'oe-commandbar-mainWrapper';
        this.el.append(this._mainWrapperElement);
        this.el.addEventListener('mousedown', event => {
            event.stopPropagation();
        });
    }

    destroy() {
        this.el.remove();
    }

    render(commands) {
        this._mainWrapperElement.innerHTML = '';
        clearTimeout(this._renderingTimeout);
        this._hoverActive = false;

        if (commands.length === 0) {
            const groupWrapperEl = document.createElement('div');
            groupWrapperEl.className = 'oe-commandbar-groupWrapper';
            const groupNameEl = document.createElement('div');
            groupNameEl.className = 'oe-commandbar-noResult';
            groupWrapperEl.append(groupNameEl);
            this._mainWrapperElement.append(groupWrapperEl);
            groupNameEl.innerText = this.options._t('No results');
            return;
        }

        this._currentSelectedCommand =
            commands.find(c => c === this._currentSelectedCommand) || commands[0];
        const groups = {};
        for (const command of commands) {
            groups[command.groupName] = groups[command.groupName] || [];
            groups[command.groupName].push(command);
        }
        for (const [groupName, commands] of Object.entries(groups)) {
            const groupWrapperEl = document.createElement('div');
            groupWrapperEl.className = 'oe-commandbar-groupWrapper';
            const groupNameEl = document.createElement('div');
            groupNameEl.className = 'oe-commandbar-groupName';
            groupWrapperEl.append(groupNameEl);
            this._mainWrapperElement.append(groupWrapperEl);
            groupNameEl.innerText = groupName;
            for (const command of commands) {
                const commandElWrapper = document.createElement('div');
                commandElWrapper.className = 'oe-commandbar-commandWrapper';
                if (this._currentSelectedCommand === command) {
                    commandElWrapper.classList.add('active');
                    // use setTimeout in order to avoid to call it upon the
                    // first rendering.
                    this._renderingTimeout = setTimeout(() => {
                        commandElWrapper.scrollIntoView({
                            block: 'nearest',
                            inline: 'nearest',
                        });
                    });
                }

                commandElWrapper.innerHTML = `
                    <div class="oe-commandbar-commandLeftCol">
                        <i class="oe-commandbar-commandImg fa"></i>
                    </div>
                    <div class="oe-commandbar-commandRightCol">
                        <div class="oe-commandbar-commandTitle">
                        </div>
                        <div class="oe-commandbar-commandDescription">
                        </div>
                    </div>
                `;
                const commandImgEl = commandElWrapper.querySelector('.oe-commandbar-commandImg');
                const commandTitleEl = commandElWrapper.querySelector(
                    '.oe-commandbar-commandTitle',
                );
                const commandDescriptionEl = commandElWrapper.querySelector(
                    '.oe-commandbar-commandDescription',
                );
                commandTitleEl.innerText = command.title;
                commandDescriptionEl.innerText = command.description;
                commandImgEl.classList.add(command.fontawesome);
                groupWrapperEl.append(commandElWrapper);

                const commandElWrapperMouseMove = () => {
                    if (!this._hoverActive || commandElWrapper.classList.contains('active')) {
                        return;
                    }
                    this.el
                        .querySelector('.oe-commandbar-commandWrapper.active')
                        .classList.remove('active');
                    this._currentSelectedCommand = command;
                    commandElWrapper.classList.add('active');
                };
                commandElWrapper.addEventListener('mousemove', commandElWrapperMouseMove);
                commandElWrapper.addEventListener(
                    'mousedown',
                    event => {
                        this._currentValidate();
                        event.preventDefault();
                        event.stopPropagation();
                    },
                    true,
                );
            }
        }
    }

    onKeydown(event) {
        const selection = document.getSelection();
        if (!selection.isCollapsed || !selection.rangeCount) return;

        if (
            event.key === '/' &&
            !this._active &&
            (!this.options.shouldActivate || this.options.shouldActivate())
        ) {
            this.options.onActivate && this.options.onActivate();

            const showOnceOnKeyup = () => {
                this.show();
                event.target.removeEventListener('keyup', showOnceOnKeyup, true);
                initialTarget = event.target;
                oldValue = event.target.innerText;
            };
            event.target.addEventListener('keyup', showOnceOnKeyup, true);
            this._active = true;
            this.render(this.options.commands);
            this._resetPosition();

            let initialTarget;
            let oldValue;

            const keyup = event => {
                if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                    event.preventDefault();
                    return;
                }
                if (!initialTarget) return;
                const diff = patienceDiff(
                    oldValue.split(''),
                    initialTarget.innerText.split(''),
                    true,
                );
                this._lastText = diff.bMove.join('').trim();

                if (this._lastText.match(/\s/)) {
                    this._stop();
                    return;
                }
                const term = this._lastText;

                this._currentFilteredCommands = this._filter(term);
                this.render(this._currentFilteredCommands);
                this._resetPosition();
            };
            const keydown = e => {
                if (e.key === 'Enter') {
                    e.stopImmediatePropagation();
                    this._currentValidate();
                    e.preventDefault();
                } else if (e.key === 'Escape') {
                    e.stopImmediatePropagation();
                    this._stop();
                    e.preventDefault();
                } else if (e.key === 'Backspace' && !this._lastText) {
                    this._stop();
                } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                    e.preventDefault();
                    e.stopImmediatePropagation();

                    const index = this._currentFilteredCommands.findIndex(
                        c => c === this._currentSelectedCommand,
                    );
                    if (!this._currentFilteredCommands.length || index === -1) {
                        this._currentSelectedCommand = undefined;
                    } else {
                        const n = e.key === 'ArrowDown' ? 1 : -1;
                        const newIndex = cycle(index + n, this._currentFilteredCommands.length - 1);
                        this._currentSelectedCommand = this._currentFilteredCommands[newIndex];
                    }
                    e.preventDefault();
                    this.render(this._currentFilteredCommands);
                }
            };
            const mousemove = () => {
                this._hoverActive = true;
            };

            this._stop = () => {
                this._active = false;
                this.hide();
                this._currentSelectedCommand = undefined;

                document.removeEventListener('mousedown', this._stop);
                document.removeEventListener('keyup', keyup);
                document.removeEventListener('keydown', keydown, true);
                document.removeEventListener('mousemove', mousemove);

                this.options.onStop && this.options.onStop();
            };
            this._currentValidate = () => {
                const command = this._currentFilteredCommands.find(
                    c => c === this._currentSelectedCommand,
                );
                if (command) {
                    this.options.preValidate && this.options.preValidate();
                    command.callback();
                    this.options.postValidate && this.options.postValidate();
                }
                this._stop();
            };
            document.addEventListener('mousedown', this._stop);
            document.addEventListener('keyup', keyup);
            document.addEventListener('keydown', keydown, true);
            document.addEventListener('mousemove', mousemove);
        }
    }

    show() {
        this.options.onShow && this.options.onShow();
        this.el.style.display = 'flex';
        this._resetPosition();
    }

    hide() {
        this.el.style.display = 'none';
        if (this._active) this._stop();
    }

    // -------------------------------------------------------------------------
    // private
    // -------------------------------------------------------------------------

    _filter(term) {
        let commands = this.options.commands;
        term = term.toLowerCase();
        term = term.replaceAll(/\s/g, '\\s');
        const regex = new RegExp(
            term
                .split('')
                .map(c => c.replace(/[\\^$.*+?()[\]{}|]/g, '\\$&'))
                .join('.*'),
        );
        if (term.length) {
            commands = this.options.commands.filter(command => {
                const commandText = (command.groupName + ' ' + command.title).toLowerCase();
                return commandText.match(regex);
            });
        }
        return commands;
    }

    _resetPosition() {
        const position = getRangePosition(this.el, this.options.document);
        if (!position) {
            this.hide();
            return;
        }
        const { left, top } = position;

        this.el.style.left = `${left}px`;
        this.el.style.top = `${top}px`;
    }
}
