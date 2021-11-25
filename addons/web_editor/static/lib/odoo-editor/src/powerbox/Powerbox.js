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

        this.addKeydownTrigger('/', { commands: this.options.commands });

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
                let commandImgEl, commandTitleEl, commandDescriptionEl;
                switch (command.style) {
                    case 'small':
                        commandTitleEl = document.createElement('div');
                        commandTitleEl.setAttribute('class', 'oe-commandbar-commandSmall');
                        commandTitleEl.setAttribute('title', command.description);
                        commandTitleEl.innerText = command.title;
                        commandElWrapper.append(commandTitleEl);
                        break;
                    default:
                        commandElWrapper.innerHTML = `
                    <div class="oe-commandbar-commandLeftCol">
                        <i class="oe-commandbar-commandImg fa"></i>
                    </div>
                    <div class="oe-commandbar-commandRightCol">
                        <div class="oe-commandbar-commandTitle">
                        </div>
                        <div class="oe-commandbar-commandDescription">
                        </div>
                    </div>`;
                        commandImgEl = commandElWrapper.querySelector('.oe-commandbar-commandImg');
                        commandTitleEl = commandElWrapper.querySelector(
                            '.oe-commandbar-commandTitle',
                        );
                        commandDescriptionEl = commandElWrapper.querySelector(
                            '.oe-commandbar-commandDescription',
                        );
                        commandTitleEl.innerText = command.title;
                        commandDescriptionEl.innerText = command.description;
                        commandImgEl.classList.add(command.fontawesome);
                }

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
                    ev => {
                        ev.preventDefault();
                        ev.stopImmediatePropagation();
                        this._currentValidate();
                    },
                    true,
                );
            }
        }
        this._resetPosition();
    }

    addKeydownTrigger(triggerKey, options) {
        this.options.editable.addEventListener(
            'keydown',
            ev => {
                const selection = this.options.document.getSelection();
                if (!selection.isCollapsed || !selection.rangeCount) return;
                if (
                    ev.key === triggerKey &&
                    !this._active &&
                    (!this.options.shouldActivate || this.options.shouldActivate())
                ) {
                    this.open({ ...options, openOnKeyupTarget: ev.target });
                }
            },
            true,
        );
    }

    open(openOptions) {
        this.options.onActivate && this.options.onActivate();
        this._currentOpenOptions = openOptions;

        const openOnKeyupTarget =
            this._currentOpenOptions.openOnKeyupTarget || this.options.editable;
        const onValueChangeFunction = term =>
            this._currentOpenOptions.valueChangeFunction
                ? this._currentOpenOptions.valueChangeFunction(term)
                : this._filter(term, this._currentOpenOptions.commands);

        const showOnceOnKeyup = () => {
            this.show();
            openOnKeyupTarget.removeEventListener('keyup', showOnceOnKeyup, true);
            initialTarget = openOnKeyupTarget;
            this._initialValue = openOnKeyupTarget.textContent;
        };
        openOnKeyupTarget.addEventListener('keyup', showOnceOnKeyup, true);

        this._active = true;
        this._currentFilteredCommands = this._currentOpenOptions.commands;
        this.render(this._currentOpenOptions.commands);

        let initialTarget;

        const keyup = async ev => {
            if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
                ev.preventDefault();
                return;
            }
            if (!initialTarget) return;
            const diff = patienceDiff(
                this._initialValue.split(''),
                initialTarget.textContent.split(''),
                true,
            );
            this._lastText = diff.bMove.join('');
            if (this._lastText.match(/\s/) && this._currentOpenOptions.closeOnSpace !== false) {
                this._stop();
                return;
            }
            const term = this._lastText;

            this._currentFilteredCommands =
                term === '' ? this._currentOpenOptions.commands : await onValueChangeFunction(term);
            this.render(this._currentFilteredCommands);
        };
        const keydown = ev => {
            if (ev.key === 'Enter') {
                ev.stopImmediatePropagation();
                this._currentValidate();
                ev.preventDefault();
            } else if (ev.key === 'Escape') {
                ev.stopImmediatePropagation();
                this._stop();
                ev.preventDefault();
            } else if (ev.key === 'Backspace' && !this._lastText) {
                this._stop();
            } else if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
                ev.preventDefault();
                ev.stopImmediatePropagation();

                const index = this._currentFilteredCommands.findIndex(
                    c => c === this._currentSelectedCommand,
                );
                if (!this._currentFilteredCommands.length || index === -1) {
                    this._currentSelectedCommand = undefined;
                } else {
                    const n = ev.key === 'ArrowDown' ? 1 : -1;
                    const newIndex = cycle(index + n, this._currentFilteredCommands.length - 1);
                    this._currentSelectedCommand = this._currentFilteredCommands[newIndex];
                }
                ev.preventDefault();
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

            this.options.document.removeEventListener('keyup', keyup);
            this.options.document.removeEventListener('keydown', keydown, true);
            this.options.document.removeEventListener('mousemove', mousemove);
            this.options.document.removeEventListener('mousedown', this._stop);
            if (document !== this.options.document) {
                document.removeEventListener('mousemove', mousemove);
                document.removeEventListener('mousedown', this._stop);
            }

            this.options.onStop && this.options.onStop();
        };
        this._currentValidate = () => {
            const command = this._currentFilteredCommands.find(
                c => c === this._currentSelectedCommand,
            );
            if (command) {
                !command.isIntermediateStep &&
                    (!command.shouldPreValidate || command.shouldPreValidate()) &&
                    this.options.preValidate &&
                    this.options.preValidate();
                command.callback();
                !command.isIntermediateStep &&
                    this.options.postValidate &&
                    this.options.postValidate();
            }
            if (!command || !command.isIntermediateStep) {
                this._stop();
            }
        };
        this.options.document.addEventListener('keyup', keyup);
        this.options.document.addEventListener('keydown', keydown, true);
        this.options.document.addEventListener('mousemove', mousemove);
        this.options.document.addEventListener('mousedown', this._stop);
        // If the Golbal document is diferent than the provided options.document,
        // which happend when the editor is inside an Iframe.
        // We need to listen to the mouse event on both document
        // to be sure the command bar will always close when clicking outside of it.
        if (document !== this.options.document) {
            document.addEventListener('mousemove', mousemove);
            document.addEventListener('mousedown', this._stop);
        }
    }

    nextOpenOptions(openOptions) {
        this._currentOpenOptions = openOptions;
        this._initialValue = (
            this._currentOpenOptions.openOnKeyupTarget || this.options.editable
        ).textContent;
        this._currentFilteredCommands = this._currentOpenOptions.commands;
        this.render(this._currentOpenOptions.commands);
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

    _filter(term, commands) {
        const initalCommands = commands;
        term = term.toLowerCase();
        term = term.replaceAll(/\s/g, '\\s');
        const regex = new RegExp(
            term
                .split('')
                .map(c => c.replace(/[\\^$.*+?()[\]{}|]/g, '\\$&'))
                .join('.*'),
        );
        if (term.length) {
            commands = initalCommands.filter(command => {
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
        let { left, top } = position;
        if (this.options.getContextFromParentRect) {
            const parentContextRect = this.options.getContextFromParentRect();
            left += parentContextRect.left;
            top += parentContextRect.top;
        }

        this.el.style.left = `${left}px`;
        this.el.style.top = `${top}px`;
    }
}
