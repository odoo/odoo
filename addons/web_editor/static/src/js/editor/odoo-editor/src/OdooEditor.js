/** @odoo-module **/
'use strict';

import './commands/deleteBackward.js';
import './commands/deleteForward.js';
import './commands/enter.js';
import './commands/shiftEnter.js';
import './commands/shiftTab.js';
import './commands/tab.js';
import './commands/toggleList.js';
import './commands/align.js';

import { sanitize } from './utils/sanitize.js';
import { serializeNode, unserializeNode, serializeSelection } from './utils/serialize.js';
import {
    closestBlock,
    commonParentGet,
    containsUnremovable,
    DIRECTIONS,
    endPos,
    ensureFocus,
    getCursorDirection,
    getFurthestUneditableParent,
    getListMode,
    getOuid,
    insertText,
    isColorGradient,
    nodeSize,
    preserveCursor,
    setCursorStart,
    setSelection,
    startPos,
    toggleClass,
    closestElement,
    isVisible,
    isHtmlContentSupported,
    rgbToHex,
    isFontAwesome,
    getInSelection,
    getDeepRange,
    getRowIndex,
    getColumnIndex,
    ancestors,
    firstLeaf,
    previousLeaf,
    nextLeaf,
    isUnremovable,
    fillEmpty,
    isEmptyBlock,
    getUrlsInfosInString,
    URL_REGEX,
    URL_REGEX_WITH_INFOS,
    isSelectionFormat,
    YOUTUBE_URL_GET_VIDEO_ID,
    unwrapContents,
    peek,
    rightPos,
    getAdjacentPreviousSiblings,
    getAdjacentNextSiblings,
    rightLeafOnlyNotBlockPath,
    isBlock,
    getTraversedNodes,
    getSelectedNodes,
    isVisibleTextNode,
    descendants,
    hasValidSelection,
    hasTableSelection,
    pxToFloat,
    parseHTML,
    splitTextNode,
    isMacOS,
    isArtificialVoidElement,
    cleanZWS,
    isZWS,
    setCursorEnd,
    paragraphRelatedElements,
    getDeepestPosition,
    leftPos,
    isNotAllowedContent,
    isEditorTab,
} from './utils/utils.js';
import { editorCommands } from './commands/commands.js';
import { Powerbox } from './powerbox/Powerbox.js';
import { TablePicker } from './tablepicker/TablePicker.js';

export * from './utils/utils.js';
import { UNBREAKABLE_ROLLBACK_CODE, UNREMOVABLE_ROLLBACK_CODE } from './utils/constants.js';
/* global DOMPurify */

const BACKSPACE_ONLY_COMMANDS = ['oDeleteBackward', 'oDeleteForward'];
const BACKSPACE_FIRST_COMMANDS = BACKSPACE_ONLY_COMMANDS.concat(['oEnter', 'oShiftEnter']);

// 60 seconds
const HISTORY_SNAPSHOT_INTERVAL = 1000 * 60;
// 10 seconds
const HISTORY_SNAPSHOT_BUFFER_TIME = 1000 * 10;

const KEYBOARD_TYPES = { VIRTUAL: 'VIRTUAL', PHYSICAL: 'PHYSICAL', UNKNOWN: 'UKNOWN' };

const IS_KEYBOARD_EVENT_UNDO = ev => ev.key === 'z' && (ev.ctrlKey || ev.metaKey);
const IS_KEYBOARD_EVENT_REDO = ev => ev.key === 'y' && (ev.ctrlKey || ev.metaKey);
const IS_KEYBOARD_EVENT_BOLD = ev => ev.key === 'b' && (ev.ctrlKey || ev.metaKey);
const IS_KEYBOARD_EVENT_ITALIC = ev => ev.key === 'i' && (ev.ctrlKey || ev.metaKey);
const IS_KEYBOARD_EVENT_UNDERLINE = ev => ev.key === 'u' && (ev.ctrlKey || ev.metaKey);
const IS_KEYBOARD_EVENT_STRIKETHROUGH = ev => ev.key === '5' && (ev.ctrlKey || ev.metaKey);
const IS_KEYBOARD_EVENT_LEFT_ARROW = ev => ev.key === 'ArrowLeft' && !(ev.ctrlKey || ev.metaKey);
const IS_KEYBOARD_EVENT_RIGHT_ARROW = ev => ev.key === 'ArrowRight' && !(ev.ctrlKey || ev.metaKey);

const CLIPBOARD_BLACKLISTS = {
    unwrap: ['.Apple-interchange-newline', 'DIV'], // These elements' children will be unwrapped.
    remove: ['META', 'STYLE', 'SCRIPT'], // These elements will be removed along with their children.
};
export const CLIPBOARD_WHITELISTS = {
    nodes: [
        // Style
        'P',
        'H1',
        'H2',
        'H3',
        'H4',
        'H5',
        'H6',
        'BLOCKQUOTE',
        'PRE',
        // List
        'UL',
        'OL',
        'LI',
        // Inline style
        'I',
        'B',
        'U',
        'S',
        'EM',
        'FONT',
        'STRONG',
        // Table
        'TABLE',
        'THEAD',
        'TH',
        'TBODY',
        'TR',
        'TD',
        // Miscellaneous
        'IMG',
        'BR',
        'A',
        '.fa',
    ],
    classes: [
        // Media
        /^float-/,
        'd-block',
        'mx-auto',
        'img-fluid',
        'img-thumbnail',
        'rounded',
        'rounded-circle',
        'table',
        'table-bordered',
        /^padding-/,
        /^shadow/,
        // Odoo colors
        /^text-o-/,
        /^bg-o-/,
        // Odoo lists
        'o_checked',
        'o_checklist',
        'oe-nested',
        // Miscellaneous
        /^btn/,
        /^fa/,
    ],
    attributes: ['class', 'href', 'src', 'target'],
    styledTags: ['SPAN', 'B', 'STRONG', 'I', 'S', 'U', 'FONT'],
    styles: {
        'text-decoration': { defaultValues: ['', 'none'] },
        'font-weight': { defaultValues: ['', '400'] },
        'background-color': { defaultValues: ['', '#fff', '#ffffff', 'rgb(255, 255, 255)', 'rgba(255, 255, 255, 1)'] },
        'color': { defaultValues: ['', '#000', '#000000', 'rgb(0, 0, 0)', 'rgba(0, 0, 0, 1)'] },
        'font-style': { defaultValues: ['', 'none', 'normal'] },
        'text-decoration-line': { defaultValues: ['', 'none'] },
        'font-size': { defaultValues: ['', '16px'] },
    }
};

// Commands that don't require a DOM selection but take an argument instead.
const SELECTIONLESS_COMMANDS = ['addRow', 'addColumn', 'removeRow', 'removeColumn'];

function defaultOptions(defaultObject, object) {
    const newObject = Object.assign({}, defaultObject, object);
    for (const [key, value] of Object.entries(object)) {
        if (typeof value === 'undefined') {
            newObject[key] = defaultObject[key];
        }
    }
    return newObject;
}
function getImageFiles(dataTransfer) {
    return [...dataTransfer.items]
        .filter(item => item.kind === 'file' && item.type.includes('image/'))
        .map((item) => item.getAsFile());
}
function getImageUrl (file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();

        reader.readAsDataURL(file);
        reader.onloadend = (e) => {
            if (reader.error) {
                return reject(reader.error);
            }
            resolve(e.target.result);
        };
    });
}
export class OdooEditor extends EventTarget {
    constructor(editable, options = {}) {
        super();

        this.options = defaultOptions(
            {
                controlHistoryFromDocument: false,
                getContextFromParentRect: () => {
                    return { top: 0, left: 0 };
                },
                toSanitize: true,
                isRootEditable: true,
                placeholder: false,
                showEmptyElementHint: true,
                defaultLinkAttributes: {},
                plugins: [],
                getUnremovableElements: () => [],
                getReadOnlyAreas: () => [],
                getContentEditableAreas: () => [],
                getPowerboxElement: () => {
                    const selection = document.getSelection();
                    if (selection.isCollapsed && selection.rangeCount) {
                        return closestElement(selection.anchorNode, 'P, DIV');
                    }
                },
                preHistoryUndo: () => {},
                isHintBlacklisted: () => false,
                filterMutationRecords: (records) => records,
                onPostSanitize: () => {},
                direction: 'ltr',
                _t: string => string,
                allowCommandVideo: true,
                renderingClasses: [],
                allowInlineAtRoot: false,
            },
            options,
        );

        // --------------
        // Set properties
        // --------------

        this.document = options.document || document;
        this.isDestroyed = false;

        this.isMobile = matchMedia('(max-width: 767px)').matches;
        this.isFirefox = navigator.userAgent.toLowerCase().indexOf('firefox') > -1;

        // Keyboard type detection, happens only at the first keydown event.
        this.keyboardType = KEYBOARD_TYPES.UNKNOWN;

        // Wether we should check for unbreakable the next history step.
        this._checkStepUnbreakable = true;

        // All dom listeners currently active.
        this._domListeners = [];

        // Set of labels that which prevent the automatic step mechanism if
        // it contains at least one element.
        this._observerTimeoutUnactive = new Set();
        // Set of labels that which prevent the observer to be active if
        // it contains at least one element.
        this._observerUnactiveLabels = new Set();

        // The state of the dom.
        this._currentMouseState = 'mouseup';

        this._onKeyupResetContenteditableNodes = [];

        // Track if we need to rollback mutations in case unbreakable or unremovable are being added or removed.
        this._toRollback = false;

        // Map that from an node id to the dom node.
        this._idToNodeMap = new Map();

        // Instanciate plugins.
        this._plugins = [];
        for (const plugin of this.options.plugins) {
            this._pluginAdd(plugin);
        }

        // -------------------
        // Alter the editable
        // -------------------

        if (editable.innerHTML.trim() === '') {
            editable.innerHTML = '<p><br></p>';
        }
        this.initElementForEdition(editable);

        // Convention: root node is ID root.
        editable.oid = 'root';
        this._idToNodeMap.set(1, editable);
        if (this.options.toSanitize) {
            sanitize(editable);
            this.options.onPostSanitize(editable);
        }
        this.editable = editable;
        this.editable.classList.add("odoo-editor-editable");
        this.editable.setAttribute('dir', this.options.direction);

        // Set contenteditable before clone as FF updates the content at this point.
        this._activateContenteditable();

        this._collabClientId = this.options.collaborationClientId;
        this._collabClientAvatarUrl = this.options.collaborationClientAvatarUrl;

        // Collaborator selection and caret display.
        this._collabSelectionInfos = new Map();
        this._collabSelectionColor = `hsl(${(Math.random() * 360).toFixed(0)}, 75%, 50%)`;
        this._collabSelectionsContainer = this.document.createElement('div');
        this._collabSelectionsContainer.classList.add('oe-collaboration-selections-container');
        this.editable.before(this._collabSelectionsContainer);

        this.idSet(editable);
        this._historyStepsActive = true;
        this.historyReset();
        if (this.options.initialHistoryId) {
            this.historySetInitialId(this.options.initialHistoryId);
        }

        this._pluginCall('sanitizeElement', [editable]);

        // ------
        // Tables
        // ------

        // Create the table picker for the Powerbox.
        this.powerboxTablePicker = new TablePicker({
            document: this.document,
            floating: true,
            getContextFromParentRect: this.options.getContextFromParentRect,
        });
        document.body.appendChild(this.powerboxTablePicker.el);
        this.powerboxTablePicker.addEventListener('cell-selected', ev => {
            this.execCommand('insertTable', {
                rowNumber: ev.detail.rowNumber,
                colNumber: ev.detail.colNumber,
            });
        });
        // Create the table picker for the toolbar.
        this.toolbarTablePicker = new TablePicker({ document: this.document });
        this.toolbarTablePicker.addEventListener('cell-selected', ev => {
            this.execCommand('insertTable', {
                rowNumber: ev.detail.rowNumber,
                colNumber: ev.detail.colNumber,
            });
        });
        // Create the table UI.
        const parser = new DOMParser();
        for (const direction of ['row', 'column']) {
            // Create the containers and the menu toggler.
            const ui = parser.parseFromString(`<div class="o_table_ui o_${direction}_ui" style="visibility: hidden;">
                <div>
                    <span class="o_table_ui_menu_toggler fa fa-bars"></span>
                    <div class="o_table_ui_menu"></div>
                </div>
            </div>`, 'text/html').body.firstElementChild;
            const uiMenu = ui.querySelector('.o_table_ui_menu');

            // Create the move buttons.
            if (direction === 'column') {
                uiMenu.append(...parser.parseFromString(`
                    <div class="o_move_left"><span class="fa fa-chevron-left"></span>` + this.options._t('Move left') + `</div>
                    <div class="o_move_right"><span class="fa fa-chevron-right"></span>` + this.options._t('Move right') + `</div>
                `, 'text/html').body.children);
                this.addDomListener(uiMenu.querySelector('.o_move_left'), 'click', this._onTableMoveLeftClick);
                this.addDomListener(uiMenu.querySelector('.o_move_right'), 'click', this._onTableMoveRightClick);
            } else {
                uiMenu.append(...parser.parseFromString(`
                    <div class="o_move_up"><span class="fa fa-chevron-left" style="transform: rotate(90deg);"></span>` + this.options._t('Move up') + `</div>
                    <div class="o_move_down"><span class="fa fa-chevron-right" style="transform: rotate(90deg);"></span>` + this.options._t('Move down') + `</div>
                `, 'text/html').body.children);
                this.addDomListener(uiMenu.querySelector('.o_move_up'), 'click', this._onTableMoveUpClick);
                this.addDomListener(uiMenu.querySelector('.o_move_down'), 'click', this._onTableMoveDownClick);
            }

            // Create the add buttons.
            if (direction === 'column') {
                uiMenu.append(...parser.parseFromString(`
                    <div class="o_insert_left"><span class="fa fa-plus"></span>` + this.options._t('Insert left') + `</div>
                    <div class="o_insert_right"><span class="fa fa-plus"></span>` + this.options._t('Insert right') +`</div>
                `, 'text/html').body.children);
                this.addDomListener(uiMenu.querySelector('.o_insert_left'), 'click', () => this.execCommand('addColumn', 'before', this._columnUiTarget));
                this.addDomListener(uiMenu.querySelector('.o_insert_right'), 'click', () => this.execCommand('addColumn', 'after', this._columnUiTarget));
            } else {
                uiMenu.append(...parser.parseFromString(`
                    <div class="o_insert_above"><span class="fa fa-plus"></span>` + this.options._t('Insert above') + `</div>
                    <div class="o_insert_below"><span class="fa fa-plus"></span>` + this.options._t('Insert below') + `</div>
                `, 'text/html').body.children);
                this.addDomListener(uiMenu.querySelector('.o_insert_above'), 'click', () => this.execCommand('addRow', 'before', this._rowUiTarget));
                this.addDomListener(uiMenu.querySelector('.o_insert_below'), 'click', () => this.execCommand('addRow', 'after', this._rowUiTarget));
            }

            // Add the delete button.
            if (direction === 'column') {
                uiMenu.append(parser.parseFromString(`<div class="o_delete_column"><span class="fa fa-trash"></span>` + this.options._t('Delete') + `</div>
                `, 'text/html').body.firstChild)
                this.addDomListener(uiMenu.querySelector('.o_delete_column'), 'click', this._onTableDeleteColumnClick);
            } else {
                uiMenu.append(parser.parseFromString(`<div class="o_delete_row"><span class="fa fa-trash"></span>` + this.options._t('Delete') + `</div>
                `, 'text/html').body.firstChild)
                this.addDomListener(uiMenu.querySelector('.o_delete_row'), 'click', this._onTableDeleteRowClick);
            }

            this[`_${direction}Ui`] = ui;
            this.document.body.append(ui);
            this.addDomListener(ui.querySelector('.o_table_ui_menu_toggler'), 'click', this._onTableMenuTogglerClick);
        }

        // --------
        // Powerbox
        // --------

        this.powerbox = new Powerbox({
            editable: this.editable,
            getContextFromParentRect: this.options.getContextFromParentRect,
            commandFilters: this.options.powerboxFilters,
            onShow: () => {
                this.powerboxTablePicker.hide();
            },
            beforeCommand: () => {
                if (this._isPowerboxOpenOnInput) {
                    this.historyRevertUntil(this._powerboxBeforeStepIndex);
                    this.historyStep(true);
                    this._historyStepsStates.set(peek(this._historySteps).id, 'consumed');
                    ensureFocus(this.editable);
                    getDeepRange(this.editable, { select: true });
                }
            },
            afterCommand: () => {
                this.historyStep(true);
                this._isPowerboxOpenOnInput = false;
            },
            categories: [
                { name: this.options._t('Structure'), priority: 70 },
                { name: this.options._t('Format'), priority: 60 },
                { name: this.options._t('Widgets'), priority: 30 },
                ...(this.options.categories || []),
            ],
            commands: [
                {
                    category: this.options._t('Structure'),
                    name: this.options._t('Bulleted list'),
                    priority: 110,
                    description: this.options._t('Create a simple bulleted list.'),
                    fontawesome: 'fa-list-ul',
                    isDisabled: () => !this.isSelectionInBlockRoot(),
                    callback: () => {
                        this.execCommand('toggleList', 'UL');
                    },
                },
                {
                    category: this.options._t('Structure'),
                    name: this.options._t('Numbered list'),
                    priority: 100,
                    description: this.options._t('Create a list with numbering.'),
                    fontawesome: 'fa-list-ol',
                    isDisabled: () => !this.isSelectionInBlockRoot(),
                    callback: () => {
                        this.execCommand('toggleList', 'OL');
                    },
                },
                {
                    category: this.options._t('Structure'),
                    name: this.options._t('Checklist'),
                    priority: 90,
                    description: this.options._t('Track tasks with a checklist.'),
                    fontawesome: 'fa-check-square-o',
                    isDisabled: () => !this.isSelectionInBlockRoot(),
                    callback: () => {
                        this.execCommand('toggleList', 'CL');
                    },
                },
                {
                    category: this.options._t('Structure'),
                    name: this.options._t('Table'),
                    priority: 80,
                    description: this.options._t('Insert a table.'),
                    fontawesome: 'fa-table',
                    isDisabled: () => !this.isSelectionInBlockRoot(),
                    callback: () => {
                        if(this.isMobile){
                            this.execCommand('insertTable', {
                                rowNumber: this.powerboxTablePicker.rowNumber,
                                colNumber: this.powerboxTablePicker.colNumber,
                            });
                        } else {
                            this.powerboxTablePicker.show();
                        }
                    },
                },
                {
                    category: this.options._t('Format'),
                    name: this.options._t('Heading 1'),
                    priority: 50,
                    description: this.options._t('Big section heading.'),
                    fontawesome: 'fa-header',
                    isDisabled: () => !this.isSelectionInBlockRoot(),
                    callback: () => {
                        this.execCommand('setTag', 'H1');
                    },
                },
                {
                    category: this.options._t('Format'),
                    name: this.options._t('Heading 2'),
                    priority: 40,
                    description: this.options._t('Medium section heading.'),
                    fontawesome: 'fa-header',
                    isDisabled: () => !this.isSelectionInBlockRoot(),
                    callback: () => {
                        this.execCommand('setTag', 'H2');
                    },
                },
                {
                    category: this.options._t('Format'),
                    name: this.options._t('Heading 3'),
                    priority: 30,
                    description: this.options._t('Small section heading.'),
                    fontawesome: 'fa-header',
                    isDisabled: () => !this.isSelectionInBlockRoot(),
                    callback: () => {
                        this.execCommand('setTag', 'H3');
                    },
                },
                {
                    category: this.options._t('Format'),
                    name: this.options._t('Switch direction'),
                    priority: 20,
                    description: this.options._t('Switch the text\'s direction.'),
                    fontawesome: 'fa-exchange',
                    callback: () => {
                        this.execCommand('switchDirection');
                    },
                },
                {
                    category: this.options._t('Format'),
                    name: this.options._t('Text'),
                    priority: 10,
                    description: this.options._t('Paragraph block.'),
                    fontawesome: 'fa-paragraph',
                    isDisabled: () => !this.isSelectionInBlockRoot(),
                    callback: () => {
                        this.execCommand('setTag', 'P');
                    },
                },
                {
                    category: this.options._t('Widgets'),
                    name: this.options._t('3 Stars'),
                    priority: 20,
                    description: this.options._t('Insert a rating over 3 stars.'),
                    fontawesome: 'fa-star-o',
                    callback: () => {
                        let html = '\u200B<span contenteditable="false" class="o_stars o_three_stars">';
                        html += Array(3).fill().map(() => '<i class="fa fa-star-o"></i>').join('');
                        html += '</span>';
                        this.execCommand('insert', parseHTML(html));
                    },
                },
                {
                    category: this.options._t('Widgets'),
                    name: this.options._t('5 Stars'),
                    priority: 10,
                    description: this.options._t('Insert a rating over 5 stars.'),
                    fontawesome: 'fa-star',
                    callback: () => {
                        let html = '\u200B<span contenteditable="false" class="o_stars o_five_stars">';
                        html += Array(5).fill().map(() => '<i class="fa fa-star-o"></i>').join('');
                        html += '</span>';
                        this.execCommand('insert', parseHTML(html));
                    },
                },
                ...(this.options.commands || []),
                ...(!this.options.commands || !this.options.commands.find(c =>  c.name === this.options._t('Separator')) ? [
                    {
                        category: this.options._t('Structure'),
                        name: this.options._t('Separator'),
                        priority: 40,
                        description: this.options._t('Insert an horizontal rule separator.'),
                        fontawesome: 'fa-minus',
                        isDisabled: () => !this.isSelectionInBlockRoot(),
                        callback: () => {
                            this.execCommand('insertHorizontalRule');
                        },
                    }] : []),
            ],
        });

        // -----------
        // Bind events
        // -----------

        this.observerActive();

        this.addDomListener(this.editable, 'keydown', this._onKeyDown);
        this.addDomListener(this.editable, 'input', this._onInput);
        this.addDomListener(this.editable, 'beforeinput', this._onBeforeInput);
        this.addDomListener(this.editable, 'mousedown', this._onMouseDown);
        this.addDomListener(this.editable, 'mouseup', this._onMouseup);
        this.addDomListener(this.editable, 'mousemove', this._onMousemove);
        this.addDomListener(this.editable, 'paste', this._onPaste);
        this.addDomListener(this.editable, 'dragstart', this._onDragStart);
        this.addDomListener(this.editable, 'drop', this._onDrop);
        this.addDomListener(this.editable, 'copy', this._onClipboardCopy);
        this.addDomListener(this.editable, 'cut', this._onClipboardCut);

        this.addDomListener(this.document, 'selectionchange', this._onSelectionChange);
        this.addDomListener(this.document, 'selectionchange', this._handleCommandHint);
        this.addDomListener(this.document, 'keydown', this._onDocumentKeydown);
        this.addDomListener(this.document, 'keyup', this._onDocumentKeyup);
        this.addDomListener(this.document, 'mouseup', this._onDocumentMouseup);
        this.addDomListener(this.document, 'click', this._onDocumentClick);

        this.multiselectionRefresh = this.multiselectionRefresh.bind(this);
        this._resizeObserver = new ResizeObserver(this.multiselectionRefresh);
        this._resizeObserver.observe(this.document.body);
        this._resizeObserver.observe(this.editable);
        this.addDomListener(this.editable, 'scroll', this.multiselectionRefresh);

        if (this._collabClientId) {
            this._snapshotInterval = setInterval(() => {
                this._historyMakeSnapshot();
            }, HISTORY_SNAPSHOT_INTERVAL);
        }

        // -------
        // Toolbar
        // -------

        if (this.options.toolbar) {
            this.setupToolbar(this.options.toolbar);
        }
        // placeholder hint
        if (editable.textContent === '' && this.options.placeholder) {
            this._makeHint(editable.firstChild, this.options.placeholder, true);
        }
    }
    /**
     * Releases anything that was initialized.
     *
     * TODO: properly implement this.
     */
    destroy() {
        this.observerUnactive();
        this._removeDomListener();
        this.powerbox.destroy();
        this.powerboxTablePicker.el.remove();
        this._collabSelectionsContainer.remove();
        this._resizeObserver.disconnect();
        clearInterval(this._snapshotInterval);
        this._pluginCall('destroy', []);
        this.isDestroyed = true;
        // Remove table UI
        this._rowUi.remove();
        this._columnUi.remove();
    }

    setupToolbar(toolbar) {
        this.toolbar = toolbar;
        this.autohideToolbar = this.options.autohideToolbar;
        this.bindExecCommand(this.toolbar);
        // Ensure anchors in the toolbar don't trigger a hash change.
        const toolbarAnchors = this.toolbar.querySelectorAll('a');
        toolbarAnchors.forEach(a => a.addEventListener('click', e => e.preventDefault()));
        const tablepickerDropdown = this.toolbar.querySelector('.oe-tablepicker-dropdown');
        tablepickerDropdown && tablepickerDropdown.append(this.toolbarTablePicker.el);
        this.toolbarTablePicker.show();
        const tableDropdownButton = this.toolbar.querySelector('#tableDropdownButton');
        tableDropdownButton &&
            tableDropdownButton.addEventListener('click', () => {
                this.toolbarTablePicker.reset();
            });
        for (const colorLabel of this.toolbar.querySelectorAll('label')) {
            colorLabel.addEventListener('mousedown', ev => {
                // Hack to prevent loss of focus (done by preventDefault) while still opening
                // color picker dialog (which is also prevented by preventDefault on chrome,
                // except when click detail is 2, which happens on a double-click but isn't
                // triggered by a dblclick event)
                if (ev.detail < 2) {
                    ev.preventDefault();
                    ev.currentTarget.dispatchEvent(new MouseEvent('click', { detail: 2 }));
                }
            });
            colorLabel.addEventListener('input', ev => {
                this.document.execCommand(ev.target.name, false, ev.target.value);
                this.updateColorpickerLabels();
            });
        }
    }

    resetContent(value) {
        value = value || '<p><br></p>';
        this.editable.innerHTML = value;
        this.sanitize(this.editable);
        this.historyStep(true);
        // The unbreakable protection mechanism detects an anomaly and attempts
        // to trigger a rollback when the content is reset using `innerHTML`.
        // Prevent this rollback as it would otherwise revert the new content.
        this._toRollback = false;
        // Placeholder hint.
        if (this.editable.textContent === '' && this.options.placeholder) {
            this._makeHint(this.editable.firstChild, this.options.placeholder, true);
        }
    }

    sanitize(target) {
        this.observerFlush();

        let record;
        if (!target) {
            // If the target is not given,
            // find the closest common ancestor to all the nodes referenced
            // in the mutations from the last step.
            for (record of this._currentStep.mutations) {
                const node = this.idFind(record.parentId || record.id) || this.editable;
                target = target
                    ? commonParentGet(target, node, this.editable)
                    : node;
            }
        }
        if (!target) {
            return false;
        }

        // If the common ancestor is in a nested list, make sure to sanitize
        // that list's parent <li> instead, so there is enough context to
        // potentially merge sibling nested lists
        // (eg, <ol>
        //          <li class="oe-nested"><ul>...</ul></li>
        //          <li class="oe-nested"><ul>...</ul></li>
        //      </ol>: these two lists should be merged together so the common
        // ancestor should be the <ol> element).
        const nestedListAncestor = closestElement(target, '.oe-nested');
        if (nestedListAncestor && nestedListAncestor.parentElement) {
            target = nestedListAncestor.parentElement;
        }

        // sanitize and mark current position as sanitized
        sanitize(target);
        this._pluginCall('sanitizeElement',
                         [target.parentElement || target]);
        this.options.onPostSanitize(target);
    }

    addDomListener(element, eventName, callback) {
        const boundCallback = callback.bind(this);
        this._domListeners.push([element, eventName, boundCallback]);
        element.addEventListener(eventName, boundCallback);
    }

    _generateId() {
        // No need for secure random number.
        return Math.floor(Math.random() * Math.pow(2,52)).toString();
    }

    // Assign IDs to src, and dest if defined
    idSet(node, testunbreak = false) {
        if (!node.oid) {
            node.oid = this._generateId();
        }
        // In case the id was created by another collaboration client.
        this._idToNodeMap.set(node.oid, node);
        // Rollback if node.ouid changed. This ensures that nodes never change
        // unbreakable ancestors.
        node.ouid = node.ouid || getOuid(node, true);
        if (testunbreak && !(node.nodeType === Node.TEXT_NODE && !node.length)) {
            const ouid = getOuid(node);
            if (!this._toRollback && ouid && ouid !== node.ouid) {
                this._toRollback = UNBREAKABLE_ROLLBACK_CODE;
            }
        }

        let childNode = node.firstChild;
        while (childNode) {
            this.idSet(childNode, testunbreak);
            childNode = childNode.nextSibling;
        }
    }

    idFind(id) {
        return this._idToNodeMap.get(id);
    }

    serializeNode(node, mutatedNodes) {
        return this._collabClientId ? serializeNode(node, mutatedNodes) : node;
    }

    unserializeNode(node) {
        return this._collabClientId ? unserializeNode(node) : node;
    }

    automaticStepActive(label) {
        this._observerTimeoutUnactive.delete(label);
    }
    automaticStepUnactive(label) {
        this._observerTimeoutUnactive.add(label);
    }
    automaticStepSkipStack() {
        this.automaticStepUnactive('skipStack');
        setTimeout(() => this.automaticStepActive('skipStack'));
    }
    observerUnactive(label) {
        this._observerUnactiveLabels.add(label);
        if (this.observer) {
            clearTimeout(this.observerTimeout);
            this.observerFlush();
            this.dispatchEvent(new Event('observerUnactive'));
            this.observer.disconnect();
        }
    }
    observerFlush() {
        this.observerApply(this.filterMutationRecords(this.observer.takeRecords()));
    }
    observerActive(label) {
        this._observerUnactiveLabels.delete(label);
        if (this._observerUnactiveLabels.size !== 0) return;

        if (!this.observer) {
            this.observer = new MutationObserver(records => {
                records = this.filterMutationRecords(records);
                if (!records.length) return;
                this.dispatchEvent(new Event('contentChanged'));
                clearTimeout(this.observerTimeout);
                if (this._observerTimeoutUnactive.size === 0) {
                    this.observerTimeout = setTimeout(() => {
                        this.historyStep();
                    }, 100);
                }
                this.observerApply(records);
            });
        }
        this.dispatchEvent(new Event('preObserverActive'));
        this.observer.observe(this.editable, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeOldValue: true,
            characterData: true,
            characterDataOldValue: true,
        });
        this.dispatchEvent(new Event('observerActive'));
    }

    observerApply(records) {
        // There is a case where node A is added and node B is a descendant of
        // node A where node B was not in the observed tree) then node B is
        // added into another node. In that case, we need to keep track of node
        // B so when serializing node A, we strip node B from the node A tree to
        // avoid the duplication of node A.
        const mutatedNodes = new Set();
        for (const record of records) {
            if (record.type === 'childList') {
                for (const node of record.addedNodes) {
                    this.idSet(node, this._checkStepUnbreakable);
                    mutatedNodes.add(node.oid);
                }
                for (const node of record.removedNodes) {
                    this.idSet(node, this._checkStepUnbreakable);
                    mutatedNodes.delete(node.oid);
                }
            }
        }
        for (const record of records) {
            switch (record.type) {
                case 'characterData': {
                    this._currentStep.mutations.push({
                        'type': 'characterData',
                        'id': record.target.oid,
                        'text': record.target.textContent,
                        'oldValue': record.oldValue,
                    });
                    break;
                }
                case 'attributes': {
                    this._currentStep.mutations.push({
                        'type': 'attributes',
                        'id': record.target.oid,
                        'attributeName': record.attributeName,
                        'value': record.target.getAttribute(record.attributeName),
                        'oldValue': record.oldValue,
                    });
                    break;
                }
                case 'childList': {
                    record.addedNodes.forEach(added => {
                        this._toRollback =
                            this._toRollback ||
                            (containsUnremovable(added) && UNREMOVABLE_ROLLBACK_CODE);
                        const mutation = {
                            'type': 'add',
                        };
                        if (!record.nextSibling && record.target.oid) {
                            mutation.append = record.target.oid;
                        } else if (record.nextSibling && record.nextSibling.oid) {
                            mutation.before = record.nextSibling.oid;
                        } else if (!record.previousSibling && record.target.oid) {
                            mutation.prepend = record.target.oid;
                        } else if (record.previousSibling && record.previousSibling.oid) {
                            mutation.after = record.previousSibling.oid;
                        } else {
                            return false;
                        }
                        mutation.id = added.oid;
                        mutation.node = this.serializeNode(added, mutatedNodes);
                        this._currentStep.mutations.push(mutation);
                    });
                    record.removedNodes.forEach(removed => {
                        if (!this._toRollback && containsUnremovable(removed)) {
                            this._toRollback = UNREMOVABLE_ROLLBACK_CODE;
                        }
                        this._currentStep.mutations.push({
                            'type': 'remove',
                            'id': removed.oid,
                            'parentId': record.target.oid,
                            'node': this.serializeNode(removed),
                            'nextId': record.nextSibling ? record.nextSibling.oid : undefined,
                            'previousId': record.previousSibling
                                ? record.previousSibling.oid
                                : undefined,
                        });
                    });
                    break;
                }
            }
        }
        if (records.length) {
            this.dispatchEvent(new Event('observerApply'));
        }
    }
    filterMutationRecords(records) {
        // Save the first attribute in a cache to compare only the first
        // attribute record of node to its latest state.
        const attributeCache = new Map();
        const filteredRecords = [];

        for (const record of records) {
            if (record.type === 'attributes') {
                // Skip the attributes change on the dom.
                if (record.target === this.editable) continue;
                if (record.attributeName === 'contenteditable') {
                    continue;
                }

                attributeCache.set(record.target, attributeCache.get(record.target) || {});
                if (record.attributeName === 'class') {
                    const classBefore = (record.oldValue && record.oldValue.split(' ')) || [];
                    const classAfter = (record.target.className && record.target.className.split && record.target.className.split(' ')) || [];
                    const excludedClasses = [];
                    for (const klass of classBefore) {
                        if (!classAfter.includes(klass)) {
                            excludedClasses.push(klass);
                        }
                    }
                    for (const klass of classAfter) {
                        if (!classBefore.includes(klass)) {
                            excludedClasses.push(klass);
                        }
                    }
                    if (excludedClasses.every(c => this.options.renderingClasses.includes(c))) {
                        continue;
                    }
                }
                if (
                    typeof attributeCache.get(record.target)[record.attributeName] === 'undefined'
                ) {
                    const oldValue = record.oldValue === undefined ? null : record.oldValue;
                    attributeCache.get(record.target)[record.attributeName] =
                        oldValue !== record.target.getAttribute(record.attributeName);
                }
                if (!attributeCache.get(record.target)[record.attributeName]) {
                    continue;
                }
            }
            if (record.target && [Node.TEXT_NODE, Node.ELEMENT_NODE].includes(record.target.nodeType)) {
                const closestProtected = closestElement(record.target, '[data-oe-protected="true"]');
                if (closestProtected && closestProtected.nodeType === Node.ELEMENT_NODE &&
                    record.target !== closestProtected) {
                    continue;
                }
            }
            filteredRecords.push(record);
        }
        return this.options.filterMutationRecords(filteredRecords);
    }

    // History
    // -------------------------------------------------------------------------

    historyReset() {
        this._historyClean();
        const firstStep = this._historyGetSnapshotStep();
        this._firstStepId = firstStep.id;
        this._historySnapshots = [{ step: firstStep }];
        this._historySteps.push(firstStep);
        // The historyIds carry the ids of the steps that were dropped when
        // doing a snapshot.
        // Those historyIds are used to compare if the last step saved in the
        // server is present in the current historySteps or historyIds to
        // ensure it is the same history branch.
        this._historyIds = [];
    }
    /**
     * Set the initial document history id.
     *
     * To prevent a saving a document with a diverging history, we store the
     * last history id in the first node of the document to the database.
     * This method provide the initial document history id to the editor.
     */
    historySetInitialId(id) {
        this._historyIds.unshift(id);
    }
    /**
     * Get all the history ids for the current history branch.
     *
     * See `_historyIds` in `historyReset`.
     */
    historyGetBranchIds() {
        return this._historyIds.concat(this._historySteps.map(s => s.id));
    }
    historyGetSnapshotSteps() {
        // If the current snapshot has no time, it means that there is the no
        // other snapshot that have been made (either it is the one created upon
        // initialization or reseted by historyResetFromSteps).
        if (!this._historySnapshots[0].time) {
            return { steps: this._historySteps, historyIds: this.historyGetBranchIds() };
        }
        const steps = [];
        let snapshot;
        if (this._historySnapshots[0].time + HISTORY_SNAPSHOT_BUFFER_TIME < Date.now()) {
            snapshot = this._historySnapshots[0];
        } else {
            // this._historySnapshots[1] has being created at least 1 minute ago
            // (HISTORY_SNAPSHOT_INTERVAL) or it is the first step.
            snapshot = this._historySnapshots[1];
        }
        let index = this._historySteps.length - 1;
        while (this._historySteps[index].id !== snapshot.step.id) {
            steps.push(this._historySteps[index]);
            index--;
        }
        steps.push(snapshot.step);
        steps.reverse();

        return { steps, historyIds: this.historyGetBranchIds() };
    }
    historyResetFromSteps(steps, historyIds) {
        this._historyIds = historyIds;
        this.observerUnactive();
        for (const node of [...this.editable.childNodes]) {
            node.remove();
        }
        this._historyClean();
        for (const step of steps) {
            this.historyApply(step.mutations);
        }
        this._historySnapshots = [{ step: steps[0] }];
        this._historySteps = steps;

        this._handleCommandHint();
        this.multiselectionRefresh();
        this.observerActive();
        this.dispatchEvent(new Event('historyResetFromSteps'));
    }
    historyGetMissingSteps({fromStepId, toStepId}) {
        const fromIndex = this._historySteps.findIndex(x => x.id === fromStepId);
        const toIndex = this._historySteps.findIndex(x => x.id === toStepId);
        if (fromIndex === -1 || toIndex === -1) {
            return -1;
        }
        return this._historySteps.slice(fromIndex + 1, toIndex);
    }

    // One step completed: apply to vDOM, setup next history step
    historyStep(skipRollback = false, { stepId } = {}) {
        if (!this._historyStepsActive) {
            return;
        }
        this.sanitize();
        // check that not two unBreakables modified
        if (this._toRollback) {
            if (!skipRollback) this.historyRollback();
            this._toRollback = false;
        }

        // push history
        const currentStep = this._currentStep;
        if (!currentStep.mutations.length) {
            return false;
        }

        currentStep.id = stepId || this._generateId();
        const previousStep = peek(this._historySteps);
        currentStep.clientId = this._collabClientId;
        currentStep.previousStepId = previousStep.id;

        this._historySteps.push(currentStep);
        if (this.options.onHistoryStep) {
            this.options.onHistoryStep(currentStep);
        }
        this._currentStep = {
            selection: {},
            mutations: [],
        };
        this._checkStepUnbreakable = true;
        this._recordHistorySelection();
        this.dispatchEvent(new Event('historyStep'));
        this.multiselectionRefresh();
    }
    // apply changes according to some records
    historyApply(records) {
        for (const record of records) {
            if (record.type === 'characterData') {
                const node = this.idFind(record.id);
                if (node) {
                    node.textContent = record.text;
                }
            } else if (record.type === 'attributes') {
                const node = this.idFind(record.id);
                if (node) {
                    let value = record.value;
                    if (typeof value === 'string' && record.attributeName === 'class') {
                        value = value.split(' ').filter(c => !this.options.renderingClasses.includes(c)).join(' ');
                    }
                    if (this._collabClientId) {
                        this._safeSetAttribute(node, record.attributeName, value);
                    } else {
                        node.setAttribute(record.attributeName, value);
                    }
                }
            } else if (record.type === 'remove') {
                const toremove = this.idFind(record.id);
                if (toremove) {
                    toremove.remove();
                }
            } else if (record.type === 'add') {
                let node = this.idFind(record.oid) || this.unserializeNode(record.node);
                if (this._collabClientId) {
                    const fakeNode = document.createElement('fake-el');
                    fakeNode.appendChild(node);
                    DOMPurify.sanitize(fakeNode, { IN_PLACE: true });
                    node = fakeNode.childNodes[0];
                    if (!node) {
                        continue;
                    }
                }

                this.idSet(node, true);

                if (record.append && this.idFind(record.append)) {
                    this.idFind(record.append).append(node);
                } else if (record.before && this.idFind(record.before)) {
                    this.idFind(record.before).before(node);
                } else if (record.after && this.idFind(record.after)) {
                    this.idFind(record.after).after(node);
                } else {
                    continue;
                }
            }
        }
    }
    historyRollback(until = 0) {
        const step = this._currentStep;
        this.observerFlush();
        this.historyRevert(step, { until });
        this.observerFlush();
        step.mutations = step.mutations.slice(0, until);
        this._toRollback = false;
    }
    /**
     * Undo the current non-recorded draft step.
     */
    historyRevertCurrentStep() {
        this.observerFlush();
        this.historyRevert(this._currentStep, {sideEffect: false});
        this.observerFlush();
        // Clear current step from all previous changes.
        this._currentStep.mutations = [];

        this._activateContenteditable();
        this.historySetSelection(this._currentStep);
    }
    /**
     * Undo a step of the history.
     *
     * this._historyStepsState is a map from it's location (index) in this.history to a state.
     * The state can be on of:
     * undefined: the position has never been undo or redo.
     * "redo": The position is considered as a redo of another.
     * "undo": The position is considered as a undo of another.
     * "consumed": The position has been undone and is considered consumed.
     */
    historyUndo() {
        this.options.preHistoryUndo();
        // The last step is considered an uncommited draft so always revert it.
        const lastStep = this._currentStep;
        this.historyRevert(lastStep);
        // Clean the last step otherwise if no other step is created after, the
        // mutations of the revert itself will be added to the same step and
        // grow exponentially at each undo.
        lastStep.mutations = [];

        const pos = this._getNextUndoIndex();
        if (pos > 0) {
            // Consider the position consumed.
            this._historyStepsStates.set(this._historySteps[pos].id, 'consumed');
            this.historyRevert(this._historySteps[pos]);
            // Consider the last position of the history as an undo.
            const stepId = this._generateId();
            this._historyStepsStates.set(stepId, 'undo');
            this.historyStep(true, { stepId });
            this.dispatchEvent(new Event('historyUndo'));
        }
    }
    /**
     * Redo a step of the history.
     *
     * @see historyUndo
     */
    historyRedo() {
        const pos = this._getNextRedoIndex();
        if (pos > 0) {
            this._historyStepsStates.set(this._historySteps[pos].id, 'consumed');
            this.historyRevert(this._historySteps[pos]);
            this.historySetSelection(this._historySteps[pos]);
            const stepId = this._generateId();
            this._historyStepsStates.set(stepId, 'redo');
            this.historyStep(true, { stepId });
            this.dispatchEvent(new Event('historyRedo'));
        }
    }
    /**
     * Check wether undoing is possible.
     */
    historyCanUndo() {
        return this._getNextUndoIndex() > 0;
    }
    /**
     * Check wether redoing is possible.
     */
    historyCanRedo() {
        return this._getNextRedoIndex() > 0;
    }
    historySize() {
        return this._historySteps.length;
    }

    historyRevert(step, { until = 0, sideEffect = true } = {} ) {
        // apply dom changes by reverting history steps
        for (let i = step.mutations.length - 1; i >= until; i--) {
            const mutation = step.mutations[i];
            if (!mutation) {
                break;
            }
            switch (mutation.type) {
                case 'characterData': {
                    const node = this.idFind(mutation.id);
                    if (node) node.textContent = mutation.oldValue;
                    break;
                }
                case 'attributes': {
                    const node = this.idFind(mutation.id);
                    if (node) {
                        if (mutation.oldValue) {
                            let value = mutation.oldValue;
                            if (typeof value === 'string' && mutation.attributeName === 'class') {
                                value = value.split(' ').filter(c => !this.options.renderingClasses.includes(c)).join(' ');
                            }
                            if (this._collabClientId) {
                                this._safeSetAttribute(node, mutation.attributeName, value);
                            } else {
                                node.setAttribute(mutation.attributeName, value);
                            }
                        } else {
                            node.removeAttribute(mutation.attributeName);
                        }
                    }
                    break;
                }
                case 'remove': {
                    let nodeToRemove = this.idFind(mutation.id);
                    if (!nodeToRemove) {
                        nodeToRemove = this.unserializeNode(mutation.node);
                        const fakeNode = document.createElement('fake-el');
                        fakeNode.appendChild(nodeToRemove);
                        DOMPurify.sanitize(fakeNode, { IN_PLACE: true });
                        nodeToRemove = fakeNode.childNodes[0];
                        if (!nodeToRemove) {
                            continue;
                        }
                        this.idSet(nodeToRemove);
                    }
                    if (mutation.nextId && this.idFind(mutation.nextId)) {
                        const node = this.idFind(mutation.nextId);
                        node && node.before(nodeToRemove);
                    } else if (mutation.previousId && this.idFind(mutation.previousId)) {
                        const node = this.idFind(mutation.previousId);
                        node && node.after(nodeToRemove);
                    } else {
                        const node = this.idFind(mutation.parentId);
                        node && node.append(nodeToRemove);
                    }
                    break;
                }
                case 'add': {
                    const node = this.idFind(mutation.id);
                    if (node) {
                        node.remove();
                    }
                }
            }
        }
        if (sideEffect) {
            if (!this._fixLinkMutatedElements) {
                this._activateContenteditable();
            }
            this.historySetSelection(step);
            this.dispatchEvent(new Event('historyRevert'));
        }
    }
    /**
     * Place the selection on the last known selection position from the history
     * steps.
     *
     * @param {boolean} [limitToEditable=false] When true returns the latest selection that
     *     happened within the editable.
     * @returns {boolean}
     */
    historyResetLatestComputedSelection(limitToEditable) {
        const computedSelection = limitToEditable
            ? this._latestComputedSelectionInEditable
            : this._latestComputedSelection;
        if (computedSelection && computedSelection.anchorNode) {
            const anchorNode = this.idFind(computedSelection.anchorNode.oid);
            const focusNode = this.idFind(computedSelection.focusNode.oid) || anchorNode;
            if (anchorNode) {
                setSelection(
                    anchorNode,
                    computedSelection.anchorOffset,
                    focusNode,
                    computedSelection.focusOffset,
                );
                return true;
            }
        }
        return false;
    }
    historySetSelection(step) {
        this.deselectTable();
        if (step.selection && step.selection.anchorNodeOid) {
            const anchorNode = this.idFind(step.selection.anchorNodeOid);
            const focusNode = this.idFind(step.selection.focusNodeOid) || anchorNode;
            if (anchorNode) {
                setSelection(
                    anchorNode,
                    step.selection.anchorOffset,
                    focusNode,
                    step.selection.focusOffset !== undefined
                        ? step.selection.focusOffset
                        : step.selection.anchorOffset,
                    false,
                );
                // If a table must be selected, ensure it's in the same tick.
                this._handleSelectionInTable();
            }
        }
    }
    unbreakableStepUnactive() {
        this._toRollback =
            this._toRollback === UNBREAKABLE_ROLLBACK_CODE ? false : this._toRollback;
        this._checkStepUnbreakable = false;
    }
    historyPauseSteps() {
        this._historyStepsActive = false;
    }
    historyUnpauseSteps() {
        this._historyStepsActive = true;
    }
    /**
     * Stash the mutations of the current step to re-apply them later.
     */
    historyStash() {
        if (!this._historyStashedMutations) {
            this._historyStashedMutations = [];
        }
        this._historyStashedMutations.push(...this._currentStep.mutations);
        this._currentStep.mutations = [];
    }
    /**
     * Unstash the previously stashed mutations into the current step.
     */
    historyUnstash() {
        if (!this._currentStep.mutations) {
            this._currentStep.mutations = [];
        }
        this._currentStep.mutations.unshift(...this._historyStashedMutations);
        this._historyStashedMutations = [];
    }
    _historyClean() {
        this._historySteps = [];
        this._currentStep = {
            selection: {
                anchorNodeOid: undefined,
                anchorOffset: undefined,
                focusNodeOid: undefined,
                focusOffset: undefined,
            },
            mutations: [],
            id: undefined,
            clientId: undefined,
        };
        this._historyStepsStates = new Map();
    }
    _historyGetSnapshotStep() {
        return {
            selection: {
                anchorNode: undefined,
                anchorOffset: undefined,
                focusNode: undefined,
                focusOffset: undefined,
            },
            mutations: Array.from(this.editable.childNodes).map(node => ({
                type: 'add',
                append: 1,
                id: node.oid,
                node: this.serializeNode(node),
            })),
            id: this._generateId(),
            clientId: this.clientId,
            previousStepId: undefined,
        };
    }
    _historyMakeSnapshot() {
        if (
            !this._lastSnapshotHistoryLength ||
            this._lastSnapshotHistoryLength < this._historySteps.length
        ) {
            this._lastSnapshotHistoryLength = this._historySteps.length;
            const step = this._historyGetSnapshotStep();
            step.id = this._historySteps[this._historySteps.length - 1].id;
            const snapshot = {
                time: Date.now(),
                step: step,
            };
            this._historySnapshots = [snapshot, this._historySnapshots[0]];
        }
    }
    /**
     * Insert a step from another collaborator.
     */
    _historyAddExternalStep(newStep) {
        let index = this._historySteps.length - 1;
        while (index >= 0 && this._historySteps[index].id !== newStep.previousStepId) {
            // Skip steps that are already in the list.
            if (this._historySteps[index].id === newStep.id) {
                return;
            }
            index--;
        }

        // When the previousStepId is not present in the this._historySteps it
        // could be either:
        // - the previousStepId is before a snapshot of the same history
        // - the previousStepId has not been received because clients were
        //   disconnected at that time
        // - the previousStepId is in another history (in case two totally
        //   differents this._historySteps (but it should not arise)).
        if (index < 0) {
            if (this.options.onHistoryMissingParentSteps) {
                const historySteps = this._historySteps;
                let index = historySteps.length - 1;
                // Get the last known step that we are sure the missing step
                // client has. It could either be a step that has the same
                // clientId or the first step.
                while(index !== 0) {
                    if (historySteps[index].clientId === newStep.clientId) {
                        break;
                    }
                    index--;
                }
                const fromStepId = historySteps[index].id;
                this.options.onHistoryMissingParentSteps({
                    step: newStep,
                    fromStepId: fromStepId,
                });
            }
            return;
        }

        let concurentSteps = [];
        index++;
        while (index < this._historySteps.length) {
            if (this._historySteps[index].previousStepId === newStep.previousStepId) {
                if (this._historySteps[index].id.localeCompare(newStep.id) === 1) {
                    break;
                } else {
                    concurentSteps = [this._historySteps[index].id];
                }
            } else {
                if (concurentSteps.includes(this._historySteps[index].previousStepId)) {
                    concurentSteps.push(this._historySteps[index].id);
                } else {
                    break;
                }
            }
            index++;
        }

        const stepsAfterNewStep = this._historySteps.slice(index);

        for (const stepToRevert of stepsAfterNewStep.slice().reverse()) {
            this.historyRevert(stepToRevert, { sideEffect: false });
        }
        this.historyApply(newStep.mutations);
        this._historySteps.splice(index, 0, newStep);
        for (const stepToApply of stepsAfterNewStep) {
            this.historyApply(stepToApply.mutations);
        }
    }
    collaborationSetClientId(id) {
        this._collabClientId = id;
    }

    onExternalHistorySteps(newSteps) {
        this.observerUnactive();
        this._computeHistorySelection();

        for (const newStep of newSteps) {
            this._historyAddExternalStep(newStep);
        }

        this.observerActive();
        this.historyResetLatestComputedSelection();
        this._handleCommandHint();
        this.multiselectionRefresh();
        this.dispatchEvent(new Event('onExternalHistorySteps'));
    }

    // Multi selection
    // -------------------------------------------------------------------------

    onExternalMultiselectionUpdate(selection) {
        this._multiselectionDisplayClient(selection);
        const { clientId } = selection;
        if (this._collabSelectionInfos.has(clientId)) {
            this._collabSelectionInfos.get(clientId).selection = selection;
        } else {
            this._collabSelectionInfos.set(clientId, { selection });
        }
    }

    multiselectionRefresh() {
        // Refresh the selection but keep the relevant images to avoid flickering.
        const avatars = [...this._collabSelectionInfos.values()].map(info => info.avatarElement);
        for (const element of this._collabSelectionsContainer.childNodes) {
            const isAvatarElement = element.classList && element.classList.contains('oe-collaboration-caret-avatar');
            if (!(isAvatarElement && avatars.includes(element))) {
                element.remove();
            }
        }
        for (const { selection } of this._collabSelectionInfos.values()) {
            this._multiselectionDisplayClient(selection);
        }
    }

    _multiselectionDisplayClient({ selection, color, clientId, clientAvatarUrl = '', clientName = this.options._t('Anonymous') }) {
        let clientRects;

        let anchorNode = this.idFind(selection.anchorNodeOid);
        let focusNode = this.idFind(selection.focusNodeOid);
        let anchorOffset = selection.anchorOffset;
        let focusOffset = selection.focusOffset;
        if (!anchorNode || !focusNode) {
            anchorNode = this.editable.children[0];
            focusNode = this.editable.children[0];
            anchorOffset = 0;
            focusOffset = 0;
        }

        [anchorNode, anchorOffset] = getDeepestPosition(anchorNode, anchorOffset);
        [focusNode, focusOffset] = getDeepestPosition(focusNode, focusOffset);

        const direction = getCursorDirection(
            anchorNode,
            anchorOffset,
            focusNode,
            focusOffset,
        );
        const range = new Range();
        try {
            if (direction === DIRECTIONS.RIGHT) {
                range.setStart(anchorNode, anchorOffset);
                range.setEnd(focusNode, focusOffset);
            } else {
                range.setStart(focusNode, focusOffset);
                range.setEnd(anchorNode, anchorOffset);
            }

            clientRects = Array.from(range.getClientRects());
        } catch {
            // Changes in the dom might prevent the range to be instantiated
            // (because of a removed node for example), in which case we ignore
            // the range.
            clientRects = [];
        }
        if (!clientRects.length) {
            return;
        }

        // Draw rects (in case the selection is not collapsed).
        const containerRect = this._collabSelectionsContainer.getBoundingClientRect();
        const indicators = clientRects.map(({ x, y, width, height }) => {
            const rectElement = this.document.createElement('div');
            rectElement.style = `
                position: absolute;
                top: ${y - containerRect.y}px;
                left: ${x - containerRect.x}px;
                width: ${width}px;
                height: ${height}px;
                background-color: ${color};
                opacity: 0.25;
                pointer-events: none;
            `;
            rectElement.setAttribute('data-selection-client-id', clientId);
            return rectElement;
        });

        // Draw carret.
        const caretElement = this.document.createElement('div');
        caretElement.style = `border-left: 2px solid ${color}; position: absolute;`;
        caretElement.setAttribute('data-selection-client-id', clientId);
        caretElement.className = 'oe-collaboration-caret';

        // Draw carret top square.
        const caretTopSquare = this.document.createElement('div');
        caretTopSquare.className = 'oe-collaboration-caret-top-square';
        caretTopSquare.style['background-color'] = color;
        caretTopSquare.setAttribute('data-client-name', clientName);
        caretElement.append(caretTopSquare);

        // Draw user avatar.
        const selectionInfo = this._collabSelectionInfos.get(clientId);
        let caretAvatar = selectionInfo && selectionInfo.avatarElement;
        if (!caretAvatar) {
            caretAvatar = this.document.createElement('div');
            caretAvatar.className = 'oe-collaboration-caret-avatar';
            caretAvatar.style.display = 'none';
            const image = this.document.createElement('img');
            caretAvatar.append(image);
            image.onload = () => caretAvatar.style.removeProperty('display');
            image.setAttribute('src', clientAvatarUrl);
            caretAvatar.setAttribute('data-selection-client-id', clientId);
            this._collabSelectionsContainer.append(caretAvatar);
        }
        // Make sure data is up to date.
        if (selectionInfo) {
            selectionInfo.avatarElement = caretAvatar;
            selectionInfo.clientName = clientName;
        } else {
            this._collabSelectionInfos.set(clientId, { avatarElement: caretAvatar, clientName: clientName });
        }

        const anchorBlockRect = closestBlock(anchorNode).getBoundingClientRect();
        const previousTop = caretAvatar.style.top;
        const top = anchorBlockRect.y - containerRect.y + 'px';
        caretAvatar.style.top = top;
        const closestList = closestElement(anchorNode, 'ul, ol'); // Prevent overlap bullets.
        const anchorX = closestList ? closestList.getBoundingClientRect().x : anchorBlockRect.x;
        const previousLeft = caretAvatar.style.left;
        const left = anchorX - containerRect.x - 25 + 'px';
        caretAvatar.style.left = left;

        // Handle overlapping avatars.
        if (previousTop !== top || previousLeft !== left) {
            const allAvatarsInDom = [...this._collabSelectionsContainer.children].filter(child => child.classList.contains('oe-collaboration-caret-avatar'));
            for (const position of [[previousTop, previousLeft], [top, left]]) {
                // Filter clients at that position.
                const [currentTop, currentLeft] = position;
                const clients = new Map([...this._collabSelectionInfos.entries()].filter(([key, value]) => {
                    const avatarTop = value.avatarElement && value.avatarElement.style.top;
                    const avatarLeft = value.avatarElement && value.avatarElement.style.left;
                    return value.avatarElement && avatarTop === currentTop && avatarLeft === currentLeft;
                }));
                // Update avatar values for that position.
                const avatars = [...clients.values()].map(client => client.avatarElement);
                const lastInDom = allAvatarsInDom.find(avatar => avatars.includes(avatar));
                const newTitle = [...clients.values()].map(client => client.clientName).join('\n');
                for (const client of clients.values()) {
                    const avatar = client.avatarElement;
                    // Only show the number of overlapping avatars on the z-top
                    // element, and then only if there are indeed more than one
                    // at the same position.
                    if (clients.size > 1 && avatar === lastInDom) {
                        avatar.setAttribute('data-overlapping-avatars', clients.size);
                    } else {
                        avatar.removeAttribute('data-overlapping-avatars');
                    }
                    if (avatar.firstElementChild.getAttribute('title') !== newTitle) {
                        avatar.firstElementChild.setAttribute('title', newTitle);
                    }
                };
            }
        }
        if (direction === DIRECTIONS.LEFT) {
            const rect = clientRects[0];
            caretElement.style.height = `${rect.height * 1.2}px`;
            caretElement.style.top = `${rect.y - containerRect.y}px`;
            caretElement.style.left = `${rect.x - containerRect.x}px`;
        } else {
            const rect = peek(clientRects);
            caretElement.style.height = `${rect.height * 1.2}px`;
            caretElement.style.top = `${rect.y - containerRect.y}px`;
            caretElement.style.left = `${rect.right - containerRect.x}px`;
        }
        this._multiselectionRemoveClient(clientId);
        this._collabSelectionsContainer.append(caretElement, ...indicators);
    }

    multiselectionRemove(clientId) {
        this._collabSelectionInfos.delete(clientId);
        this._multiselectionRemoveClient(clientId);
        const avatars = [...this._collabSelectionsContainer.children].filter(child => (
            child.classList.contains('oe-collaboration-caret-avatar') &&
            child.getAttribute('data-selection-client-id') === clientId
        ));
        for (const avatar of avatars) {
            avatar.remove();
        }
    }

    _multiselectionRemoveClient(clientId) {
        const elements = this._collabSelectionsContainer.querySelectorAll(
            `[data-selection-client-id="${clientId}"]:not(.oe-collaboration-caret-avatar)`,
        );
        for (const element of elements) {
            element.remove();
        }
    }

    setContenteditableLink(link) {
        const editableChildren = link.querySelectorAll('[contenteditable=true]');
        this._stopContenteditable();

        this._fixLinkMutatedElements = {
            link,
            wasContenteditableTrue: [...editableChildren],
            wasContenteditableFalse: [],
            wasContenteditableNull: [],
        };
        const contentEditableAttribute = link.getAttribute('contenteditable');
        if (contentEditableAttribute === 'true') {
            this._fixLinkMutatedElements.wasContenteditableTrue.push(link);
        } else if (contentEditableAttribute === 'false') {
            this._fixLinkMutatedElements.wasContenteditableFalse.push(link);
        } else {
            this._fixLinkMutatedElements.wasContenteditableNull.push(link);
        }

        [...editableChildren, link].forEach(node => node.setAttribute('contenteditable', true));
    }

    /**
     * Same as @see _applyCommand, except that also simulates all the
     * contenteditable behaviors we let happen, e.g. the backspace handling
     * we then rollback.
     *
     * TODO this uses document.execCommand (which is deprecated) and relies on
     * the fact that using a command through it leads to the same result as
     * executing that command through a user keyboard on the unaltered editable
     * section with standard contenteditable attribute. This is already a huge
     * assomption.
     *
     * @param {string} method
     * @returns {?}
     */
    execCommand(...args) {
        this._computeHistorySelection();
        return this._applyCommand(...args);
    }

    /**
     * Find all descendants of `element` with a `data-call` attribute and bind
     * them on click to the execution of the command matching that
     * attribute.
     */
    bindExecCommand(element) {
        for (const buttonEl of element.querySelectorAll('[data-call]')) {
            buttonEl.addEventListener('click', ev => {
                const sel = this.document.getSelection();
                if (sel.anchorNode && ancestors(sel.anchorNode).includes(this.editable)) {
                    this.execCommand(buttonEl.dataset.call, buttonEl.dataset.arg1);

                    ev.preventDefault();
                    this._updateToolbar();
                }
            });
        }
    }

    /**
     * Remove any custom table selection from the editor.
     *
     * @returns {boolean} true if a table was deselected
     */
    deselectTable() {
        this.observerUnactive('deselectTable');
        let didDeselectTable = false;
        for (const td of this.editable.querySelectorAll('.o_selected_table, .o_selected_td')) {
            td.classList.remove('o_selected_td', 'o_selected_table');
            if (!td.classList.length) {
                td.removeAttribute('class');
            }
            didDeselectTable = true;
        }
        this.observerActive('deselectTable');
        return didDeselectTable;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _removeDomListener() {
        for (const [element, eventName, boundCallback] of this._domListeners) {
            element.removeEventListener(eventName, boundCallback);
        }
        this._domListeners = [];
    }

    // EDITOR COMMANDS
    // ===============

    deleteRange(sel) {
        if (this.deleteTableRange()) {
            return;
        }
        if (!this.editable.childElementCount) {
            // Ensure the editable has content.
            const p = document.createElement('p');
            p.append(document.createElement('br'));
            this.editable.append(p);
            setSelection(p, 0);
            return;
        }
        let range = getDeepRange(this.editable, {
            sel,
            splitText: true,
            select: true,
            correctTripleClick: true,
        });
        if (!range) return;
        // Expand the range to fully include all contentEditable=False elements.
        const commonAncestorContainer = this.editable.contains(range.commonAncestorContainer) ?
            range.commonAncestorContainer :
            this.editable;
        const startUneditable = getFurthestUneditableParent(range.startContainer, commonAncestorContainer);
        if (startUneditable) {
            let leaf = previousLeaf(startUneditable);
            if (leaf) {
                range.setStart(leaf, nodeSize(leaf));
            } else {
                range.setStart(commonAncestorContainer, 0);
            }
        }
        const endUneditable = getFurthestUneditableParent(range.endContainer, commonAncestorContainer);
        if (endUneditable) {
            let leaf = nextLeaf(endUneditable);
            if (leaf) {
                range.setEnd(leaf, 0);
            } else {
                range.setEnd(commonAncestorContainer, nodeSize(commonAncestorContainer));
            }
        }
        let insertedZws;
        if (sel && !sel.isCollapsed && !range.startOffset && !range.startContainer.previousSibling) {
            // Insert a zero-width space before the selection if the selection
            // is non-collapsed and at the beginning of its parent, so said
            // parent will have content after extraction. This ensures that the
            // parent will not be removed by "tricking" `range.extractContents`.
            // Eg, <h1><font>[...]</font></h1> will preserve the styles of the
            // <font> node. If it remains empty, it will be cleaned up later by
            // the sanitizer.
            const zws = document.createTextNode('\u200B');
            range.startContainer.before(zws);
            insertedZws = zws;
        }
        let start = range.startContainer;
        let end = range.endContainer;
        // Let the DOM split and delete the range.
        const doJoin =
            (closestBlock(start) !== closestBlock(range.commonAncestorContainer) ||
            closestBlock(end) !== closestBlock(range.commonAncestorContainer))
            && (closestBlock(start).tagName !== 'TD' && closestBlock(end).tagName !== 'TD');
        let next = nextLeaf(end, this.editable);
        const contents = range.extractContents();
        setSelection(start, nodeSize(start));
        range = getDeepRange(this.editable, { sel });
        // Restore unremovables removed by extractContents.
        [...contents.querySelectorAll('*')].filter(isUnremovable).forEach(n => {
            closestBlock(range.endContainer).after(n);
            n.textContent = '';
        });
        // If the end container was fully selected, extractContents may have
        // emptied it without removing it. Ensure it's gone.
        const isRemovableInvisible = (node, noBlocks = true) =>
            !isVisible(node, noBlocks) && !isUnremovable(node);
        const endIsStart = end === start;
        while (end && isRemovableInvisible(end, false) && !end.contains(range.endContainer)) {
            const parent = end.parentNode;
            end.remove();
            end = parent;
        }
        // Same with the start container
        while (
            start &&
            isRemovableInvisible(start) &&
            !(endIsStart && start.contains(range.startContainer))
        ) {
            const parent = start.parentNode;
            start.remove();
            start = parent;
        }
        // Ensure empty blocks be given a <br> child.
        if (start) {
            fillEmpty(closestBlock(start));
        }
        fillEmpty(closestBlock(range.endContainer));
        // Ensure trailing space remains visible.
        const joinWith = range.endContainer;
        const oldText = joinWith.textContent;
        const rightLeaf = rightLeafOnlyNotBlockPath(range.endContainer).next().value;
        const hasSpaceAfter = !rightLeaf || rightLeaf.textContent.startsWith(' ');
        const shouldPreserveSpace = (doJoin || hasSpaceAfter) && joinWith && oldText.endsWith(' ');
        if (shouldPreserveSpace) {
            joinWith.textContent = oldText.replace(/ $/, '\u00A0');
            setSelection(joinWith, nodeSize(joinWith));
        }
        // Rejoin blocks that extractContents may have split in two.
        while (
            doJoin &&
            next &&
            !(next.previousSibling && next.previousSibling === joinWith) &&
            this.editable.contains(next)
        ) {
            const restore = preserveCursor(this.document);
            this.observerFlush();
            const res = this._protect(() => {
                next.oDeleteBackward();
                if (!this.editable.contains(joinWith)) {
                    this._toRollback = UNREMOVABLE_ROLLBACK_CODE; // tried to delete too far -> roll it back.
                } else {
                    next = firstLeaf(next);
                }
            }, this._currentStep.mutations.length);
            if ([UNBREAKABLE_ROLLBACK_CODE, UNREMOVABLE_ROLLBACK_CODE].includes(res)) {
                restore();
                break;
            }
        }
        if (insertedZws) {
            // Remove the zero-width space (zws) that was added to preserve the
            // parent styles, then call `fillEmpty` to properly add a flagged
            // zws if still needed.
            const el = closestElement(insertedZws);
            insertedZws.remove();
            el && fillEmpty(el);
        }
        next = range.endContainer && rightLeafOnlyNotBlockPath(range.endContainer).next().value;
        if (
            shouldPreserveSpace && next && !(next && next.nodeType === Node.TEXT_NODE && next.textContent.startsWith(' '))
        ) {
            // Restore the text we modified in order to preserve trailing space.
            joinWith.textContent = oldText;
            setSelection(joinWith, nodeSize(joinWith));
        }
        if (joinWith) {
            const el = closestElement(joinWith);
            el && fillEmpty(el);
        }
    }

    /**
     * Handle range deletion in cases that involve custom table selections.
     * Return true if nodes removed _inside_ a table, false otherwise (or if the
     * table itself was removed).
     *
     * @param {Selection} sel
     * @returns {boolean}
     */
    deleteTableRange() {
        const selectedTds = this.editable.querySelectorAll('.o_selected_td');
        const fullySelectedTables = [...this.editable.querySelectorAll('.o_selected_table')].filter(table => (
            [...table.querySelectorAll('td')].every(td => td.classList.contains('o_selected_td'))
        ));
        if (selectedTds.length && !fullySelectedTables.length) {
            this.historyPauseSteps();
            // A selection within a table has to be handled differently so it
            // takes into account the custom table cell selections, and doesn't
            // break the table. If the selection includes a table cell but also
            // elements that are out of a table, the whole table will be
            // selected so its deletion can be handled separately.
            const rows = [...closestElement(selectedTds[0], 'tr').parentElement.children].filter(child => child.nodeName === 'TR');
            const firstRowCells = [...rows[0].children].filter(child => child.nodeName === 'TD' || child.nodeName === 'TH');
            const areFullColumnsSelected = getRowIndex(selectedTds[0]) === 0 && getRowIndex(selectedTds[selectedTds.length - 1]) === rows.length - 1;
            const areFullRowsSelected = getColumnIndex(selectedTds[0]) === 0 && getColumnIndex(selectedTds[selectedTds.length - 1]) === firstRowCells.length - 1;
            if (areFullColumnsSelected || areFullRowsSelected) {
                // If some full columns are selected, remove them.
                if (areFullColumnsSelected) {
                    const startIndex = getColumnIndex(selectedTds[0]);
                    let endIndex = getColumnIndex(selectedTds[selectedTds.length - 1]);
                    let currentIndex = startIndex;
                    while (currentIndex <= endIndex) {
                        this.execCommand('removeColumn', firstRowCells[currentIndex]);
                        currentIndex++;
                    }
                }
                // If some full rows are selected, remove them.
                if (areFullRowsSelected) {
                    const startIndex = getRowIndex(selectedTds[0]);
                    let endIndex = getRowIndex(selectedTds[selectedTds.length - 1]);
                    let currentIndex = startIndex;
                    while (currentIndex <= endIndex) {
                        this.execCommand('removeRow', rows[currentIndex]);
                        currentIndex++;
                    }
                }
            } else {
                // If no full row or column is selected, empty the selected cells.
                for (const td of selectedTds) {
                    [...td.childNodes].forEach(child => child.remove());
                    td.append(document.createElement('br'));
                }
            }
            this.historyUnpauseSteps();
            this.historyStep();
            return true;
        } else if (fullySelectedTables.length) {
            fullySelectedTables.forEach(table => table.remove());
        }
        return false;
    }

    /**
     * Displays the text colors (foreground ink and background highlight)
     * based on the current text cursor position. For gradients, displays
     * the average color of the gradient.
     *
     * @param {object} [params]
     * @param {string} [params.foreColor] - forces the 'foreColor' in the
     *     toolbar instead of determining it from the cursor position
     * @param {string} [params.hiliteColor] - forces the 'hiliteColor' in the
     *     toolbar instead of determining it from the cursor position
     */
    updateColorpickerLabels(params = {}) {
        function hexFromColor(color) {
            if (isColorGradient(color)) {
                // For gradients, compute the average color
                color = color.match(/gradient(.*)/)[0];
                let r = 0, g = 0, b = 0, count = 0;
                for (const entry of color.matchAll(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+(?:\.\d+)?))?\)/g)) {
                    count++;
                    r += parseInt(entry[1], 10);
                    g += parseInt(entry[2], 10);
                    b += parseInt(entry[3], 10);
                }
                color = `rgb(${Math.round(r / count)}, ${Math.round(g / count)}, ${Math.round(b / count)})`;
            }
            return rgbToHex(color);
        }
        let foreColor = params.foreColor;
        let hiliteColor = params.hiliteColor;

        // Determine colors at cursor position
        const sel = this.document.getSelection();
        if (sel.rangeCount && (!foreColor || !hiliteColor)) {
            const endContainer = closestElement(sel.getRangeAt(0).endContainer);
            const computedStyle = getComputedStyle(endContainer);
            const backgroundImage = computedStyle.backgroundImage;
            const hasGradient = isColorGradient(backgroundImage);
            const hasTextGradientClass = endContainer.classList.contains('text-gradient');
            if (!foreColor) {
                if (hasGradient && hasTextGradientClass) {
                    foreColor = backgroundImage;
                } else {
                    foreColor = this.document.queryCommandValue('foreColor');
                }
            }
            if (!hiliteColor) {
                if (hasGradient && !hasTextGradientClass) {
                    hiliteColor = backgroundImage;
                } else {
                    let ancestor = endContainer;
                    while (ancestor && !hiliteColor) {
                        hiliteColor = ancestor.style.backgroundColor;
                        ancestor = ancestor.parentElement;
                    }
                    if (!hiliteColor) {
                        hiliteColor = computedStyle.backgroundColor;
                    }
                }
            }
        }

        // display colors in toolbar buttons
        foreColor = hexFromColor(foreColor);
        this.toolbar.style.setProperty('--fore-color', foreColor);
        const foreColorInput = this.toolbar.querySelector('#foreColor input');
        if (foreColorInput) {
            foreColorInput.value = foreColor;
        }

        hiliteColor = hexFromColor(hiliteColor);
        this.toolbar.style.setProperty('--hilite-color', hiliteColor);
        const hiliteColorInput = this.toolbar.querySelector('#hiliteColor input');
        if (hiliteColorInput) {
            hiliteColorInput.value = hiliteColor.length <= 7 ? hiliteColor : hexFromColor(hiliteColor);
        }
    }

    /**
     * Applies the given command to the current selection. This does *NOT*:
     * 1) update the history cursor
     * 2) protect the unbreakables or unremovables
     * 3) sanitize the result
     * 4) create new history entry
     * 5) follow the exact same operations that would be done following events
     *    that would lead to that command
     *
     * For points 1 -> 4, @see _applyCommand
     * For points 1 -> 5, @see execCommand
     *
     * @private
     * @param {string} method
     * @returns {?}
     */
    _applyRawCommand(method, ...args) {
        const sel = this.document.getSelection();
        if (
            !(SELECTIONLESS_COMMANDS.includes(method) && args.length) && (
                !this.editable.contains(sel.anchorNode) ||
                (sel.anchorNode !== sel.focusNode && !this.editable.contains(sel.focusNode))
            )
        ) {
            // Do not apply commands out of the editable area.
            return false;
        }
        if (!sel.isCollapsed && BACKSPACE_FIRST_COMMANDS.includes(method)) {
            let range = getDeepRange(this.editable, {sel, splitText: true, select: true, correctTripleClick: true});
            if (range &&
                range.startContainer === range.endContainer &&
                range.endContainer.nodeType === Node.TEXT_NODE &&
                range.cloneContents().textContent === '\u200B'
            ) {
                // We Collapse the selection and bypass deleteRange
                // if the range content is only one ZWS.
                sel.collapseToStart();
                if (BACKSPACE_ONLY_COMMANDS.includes(method)) {
                    this._applyRawCommand(method);
                }
                return;
            }
            this.deleteRange(sel);
            if (BACKSPACE_ONLY_COMMANDS.includes(method)) {
                return true;
            }
        }
        if (editorCommands[method]) {
            // Make sure to restore the content editable before applying an
            // editor command, as it might have been temporarily disabled for
            // browser behaviors which should not concern editor commands.
            const link = this._fixLinkMutatedElements && this._fixLinkMutatedElements.link;
            if (this._fixLinkMutatedElements) {
                this.resetContenteditableLink();
                this._activateContenteditable();
            }
            const returnValue = editorCommands[method](this, ...args);
            if (link) {
                this.setContenteditableLink(link);
            }
            return returnValue;
        }
        if (method.startsWith('justify')) {
            const mode = method.split('justify').join('').toLocaleLowerCase();
            return this._align(mode === 'full' ? 'justify' : mode);
        }
        return sel.anchorNode[method](sel.anchorOffset, ...args);
    }

    /**
     * Same as @see _applyRawCommand but adapt history, protects unbreakables
     * and removables and sanitizes the result.
     *
     * @private
     * @param {string} method
     * @returns {?}
     */
    _applyCommand(...args) {
        this._recordHistorySelection(true);
        const result = this._protect(() => this._applyRawCommand(...args));
        this.historyStep();
        this._handleCommandHint();
        return result;
    }
    /**
     * @private
     * @param {function} callback
     * @param {number} [rollbackCounter]
     * @returns {?}
     */
    _protect(callback, rollbackCounter) {
        try {
            const result = callback.call(this);
            this.observerFlush();
            if (this._toRollback) {
                const torollbackCode = this._toRollback;
                this.historyRollback(rollbackCounter);
                return torollbackCode; // UNBREAKABLE_ROLLBACK_CODE || UNREMOVABLE_ROLLBACK_CODE
            } else {
                return result;
            }
        } catch (error) {
            if (error === UNBREAKABLE_ROLLBACK_CODE || error === UNREMOVABLE_ROLLBACK_CODE) {
                this.historyRollback(rollbackCounter);
                return error;
            } else {
                throw error;
            }
        }
    }
    resetContenteditableLink() {
        if (this._fixLinkMutatedElements) {
            for (const element of this._fixLinkMutatedElements.wasContenteditableTrue) {
                element.setAttribute('contenteditable', 'true');
            }
            for (const element of this._fixLinkMutatedElements.wasContenteditableFalse) {
                element.setAttribute('contenteditable', 'false');
            }
            for (const element of this._fixLinkMutatedElements.wasContenteditableNull) {
                element.removeAttribute('contenteditable');
            }
            delete this._fixLinkMutatedElements;
        }
    }
    _activateContenteditable() {
        this.observerUnactive('_activateContenteditable');
        this.editable.setAttribute('contenteditable', this.options.isRootEditable);

        const editableAreas = this.options.getContentEditableAreas(this).filter(node => !isArtificialVoidElement(node));
        for (const node of editableAreas) {
            if (!node.isContentEditable) {
                node.setAttribute('contenteditable', true);
            }
        }
        for (const node of this.options.getReadOnlyAreas()) {
            node.setAttribute('contenteditable', false);
        }
        for (const element of this.options.getUnremovableElements()) {
            element.classList.add("oe_unremovable");
        }
        this.observerActive('_activateContenteditable');
    }
    _stopContenteditable() {
        this.observerUnactive('_stopContenteditable');
        if (this.options.isRootEditable) {
            this.editable.setAttribute('contenteditable', !this.options.isRootEditable);
        }
        for (const node of this.options.getContentEditableAreas(this)) {
            if (node.getAttribute('contenteditable') === 'true') {
                node.setAttribute('contenteditable', false);
            }
        }
        this.observerActive('_stopContenteditable');
    }

    // TABLE MANAGEMENT
    // ================

    /**
     * Handle the selection of table cells rectangularly (as opposed to line by
     * line from left to right then top to bottom). If such a special selection
     * was indeed applied, return true (and false otherwise).
     *
     * @private
     * @param {MouseEvent|undefined} [ev]
     * @returns {boolean}
     */
    _handleSelectionInTable(ev=undefined) {
        const selection = this.document.getSelection();
        // Selection could be gone if the document comes from an iframe that has been removed.
        const anchorNode = selection && selection.rangeCount && selection.getRangeAt(0) && selection.anchorNode;
        if (anchorNode && !ancestors(anchorNode).includes(this.editable)) {
            return false;
        }
        this.deselectTable();
        const traversedNodes = getTraversedNodes(this.editable);
        if (this._isResizingTable || !traversedNodes.some(node => !!closestElement(node, 'td') && !closestElement(node, '[data-oe-protected="true"]'))) {
            return false;
        }
        let range;
        if (selection.rangeCount > 1) {
            // Firefox selection in table works with multiple ranges.
            const startRange = getDeepRange(this.editable, {range: selection.getRangeAt(0)});
            const endRange = getDeepRange(this.editable, {range: selection.getRangeAt(selection.rangeCount - 1)});
            range = this.document.createRange();
            range.setStart(startRange.startContainer, 0);
            range.setEnd(endRange.startContainer, 0);
        } else {
            // We need the triple click correction only for a bug in firefox
            // where it gives a selection of a full cell as tr 0 tr 1. The
            // correction makes it so it gives us the cell and not its neighbor.
            // In all other cases we don't want to make that correction so as to
            // avoid flicker when hovering borders.
            range = getDeepRange(this.editable, { correctTripleClick: anchorNode && anchorNode.nodeName === 'TR' });
        }
        const startTd = closestElement(range.startContainer, 'td');
        const endTd = closestElement(range.endContainer, 'td');
        let appliedCustomSelection = false;
        // Get the top table ancestors at range bounds.
        const startTable = ancestors(range.startContainer, this.editable).filter(node => node.nodeName === 'TABLE').pop();
        const endTable = ancestors(range.endContainer, this.editable).filter(node => node.nodeName === 'TABLE').pop();
        if (startTd !== endTd && startTable === endTable) {
            if (!closestElement(startTable, '[data-oe-protected="true"]')) {
                // The selection goes through at least two different cells ->
                // select cells.
                this._selectTableCells(range);
                appliedCustomSelection = true;
            }
        } else if (!traversedNodes.every(node => node.parentElement && closestElement(node.parentElement, 'table'))) {
            // The selection goes through a table but also outside of it ->
            // select the whole table.
            this.observerUnactive('handleSelectionInTable');
            const traversedTables = new Set(
                traversedNodes
                    .map((node) => closestElement(node, "table"))
                    .filter((node) => !closestElement(node, '[data-oe-protected="true"]'))
            );
            for (const table of traversedTables) {
                // Don't apply several nested levels of selection.
                if (table && !ancestors(table, this.editable).some(node => [...traversedTables].includes(node))) {
                    table.classList.toggle('o_selected_table', true);
                    for (const td of [...table.querySelectorAll('td')].filter(td => closestElement(td, 'table') === table)) {
                        td.classList.toggle('o_selected_td', true);
                    }
                    appliedCustomSelection = true;
                }
            }
            this.observerActive('handleSelectionInTable');
        } else if (ev && startTd && !closestElement(startTd, '[data-oe-protected="true"]')) {
            // We're redirected from a mousemove event.
            const selectedNodes = getSelectedNodes(this.editable);
            const areCellContentsFullySelected = descendants(startTd).filter(d => !isBlock(d)).every(child => selectedNodes.includes(child));
            if (areCellContentsFullySelected) {
                const SENSITIVITY = 5;
                const rangeRect = range.getBoundingClientRect();
                const isMovingAwayFromSelection = ev.clientX > rangeRect.x + rangeRect.width + SENSITIVITY // moving right
                    || ev.clientX < rangeRect.x - SENSITIVITY; // moving left
                if (isMovingAwayFromSelection) {
                    // A cell is fully selected and the mouse is moving away
                    // from the selection, within said cell -> select the cell.
                    this._selectTableCells(range);
                    appliedCustomSelection = true;
                }
            } else if (!descendants(startTd).some(child => isVisibleTextNode(child) && child.textContent !== '\u200B') &&
                ev.clientX - (this._lastMouseClickPosition ? this._lastMouseClickPosition[0] : ev.clientX) >= 15
            ) {
                // Handle selecting an empty cell.
                this._selectTableCells(range);
                appliedCustomSelection = true;
            }
        }
        return appliedCustomSelection;
    }
    /**
     * Helper function to `_handleSelectionInTable`. Do the actual selection of
     * cells in a table based on the current range.
     *
     * @private
     * @see _handleSelectionInTable
     * @param {Range} range
     */
    _selectTableCells(range) {
        this.observerUnactive('_selectTableCells');
        const table = closestElement(range.commonAncestorContainer, 'table');
        const alreadyHadSelection = table.classList.contains('o_selected_table');
        this.deselectTable(); // Undo previous selection.
        table.classList.toggle('o_selected_table', true);
        const columns = [...table.querySelectorAll('td')].filter(td => closestElement(td, 'table') === table);
        const startCol = [range.startContainer, ...ancestors(range.startContainer, this.editable)]
            .find(node => node.nodeName === 'TD' && closestElement(node, 'table') === table) || columns[0];
        const endCol = [range.endContainer, ...ancestors(range.endContainer, this.editable)]
            .find(node => node.nodeName === 'TD' && closestElement(node, 'table') === table) || columns[columns.length - 1];
        const [startRow, endRow] = [closestElement(startCol, 'tr'), closestElement(endCol, 'tr')];
        const [startColIndex, endColIndex] = [getColumnIndex(startCol), getColumnIndex(endCol)];
        const [startRowIndex, endRowIndex] = [getRowIndex(startRow), getRowIndex(endRow)];
        const [minRowIndex, maxRowIndex] = [Math.min(startRowIndex, endRowIndex), Math.max(startRowIndex, endRowIndex)];
        const [minColIndex, maxColIndex]  = [Math.min(startColIndex, endColIndex), Math.max(startColIndex, endColIndex)];
        // Create an array of arrays of tds (each of which is a row).
        const grid = [...table.querySelectorAll('tr')]
            .filter(tr => closestElement(tr, 'table') === table)
            .map(tr => [...tr.children].filter(child => child.nodeName === 'TD'));
        for (const tds of grid.filter((_, index) => index >= minRowIndex && index <= maxRowIndex)) {
            for (const td of tds.filter((_, index) => index >= minColIndex && index <= maxColIndex)) {
                td.classList.toggle('o_selected_td', true);
            }
        }
        if (!alreadyHadSelection) {
            this.toolbarShow();
        }
        this.observerActive('_selectTableCells');
    }
    /**
     * If the mouse is hovering over one of the borders of a table cell element,
     * return the side of that border ('left'|'top'|'right'|'bottom').
     * Otherwise, return false.
     *
     * @private
     * @param {MouseEvent} ev
     * @returns {boolean}
     */
    _isHoveringTdBorder(ev) {
        if (ev.target && ev.target.nodeName === 'TD' && ev.target.isContentEditable) {
            const SENSITIVITY = 5;
            const targetRect = ev.target.getBoundingClientRect();
            if (ev.clientX <= targetRect.x + SENSITIVITY) {
                return 'left';
            } else if (ev.clientY <= targetRect.y + SENSITIVITY) {
                return 'top';
            } else if (ev.clientX >= targetRect.x + ev.target.clientWidth - SENSITIVITY) {
                return 'right';
            } else if (ev.clientY >= targetRect.y + ev.target.clientHeight - SENSITIVITY) {
                return 'bottom';
            }
        }
        return false;
    }
    /**
     * Change the cursor to a resizing cursor, in the direction specified. If no
     * direction is specified, return the cursor to its default.
     *
     * @private
     * @param {'col'|'row'|false} direction 'col'/'row' to hint column/row,
     *                                      false to remove the hints
     */
    _toggleTableResizeCursor(direction) {
        this.editable.classList.remove('o_col_resize', 'o_row_resize');
        if (direction === 'col') {
            this.editable.classList.add('o_col_resize');
        } else if (direction === 'row') {
            this.editable.classList.add('o_row_resize');
        }
    }
    /**
     * Resizes a table in the given direction, by "pulling" the border between
     * the given targets (ordered left to right or top to bottom).
     *
     * @private
     * @param {MouseEvent} ev
     */
    _resizeTable(ev, direction, target1, target2) {
        ev.preventDefault();
        const position = target1 ? (target2 ? 'middle' : 'last') : 'first';
        let [item, neighbor] = [target1 || target2, target2];
        const table = closestElement(item, 'table');
        const [sizeProp, positionProp, clientPositionProp] = direction === 'col' ? ['width', 'x', 'clientX'] : ['height', 'y', 'clientY'];

        // Preserve current sizes.
        const tableRect = table.getBoundingClientRect();
        table.style[sizeProp] = tableRect[sizeProp] + 'px';
        const unsizedItemsSelector = `${direction === 'col' ? 'td' : 'tr'}:not([style*=${sizeProp}])`;
        for (const unsizedItem of table.querySelectorAll(unsizedItemsSelector)) {
            unsizedItem.style[sizeProp] = unsizedItem.getBoundingClientRect()[sizeProp] + 'px';
        }

        // TD widths should only be applied in the first row. Change targets and
        // clean the rest.
        if (direction === 'col') {
            let hostCell = closestElement(table, 'td');
            const hostCells = [];
            while (hostCell) {
                hostCells.push(hostCell);
                hostCell = closestElement(hostCell.parentElement, 'td');
            }
            const nthColumn = getColumnIndex(item);
            const firstRow = [...table.querySelector('tr').children];
            [item, neighbor] = [firstRow[nthColumn], firstRow[nthColumn + 1]];
            for (const td of hostCells) {
                if (td !== item && td !== neighbor && closestElement(td, 'table') === table && getColumnIndex(td) !== 0) {
                    td.style.removeProperty(sizeProp);
                }
            }
        }

        const MIN_SIZE = 33; // TODO: ideally, find this value programmatically.
        switch (position) {
            case 'first': {
                const marginProp = direction === 'col' ? 'marginLeft' : 'marginTop';
                const itemRect = item.getBoundingClientRect();
                const tableStyle = getComputedStyle(table);
                const currentMargin = pxToFloat(tableStyle[marginProp]);
                const sizeDelta = itemRect[positionProp] - ev[clientPositionProp];
                const newMargin = currentMargin - sizeDelta;
                const currentSize = itemRect[sizeProp];
                const newSize = currentSize + sizeDelta;
                if (newMargin >= 0 && newSize > MIN_SIZE) {
                    const tableRect = table.getBoundingClientRect();
                    // Check if a nested table would overflow its parent cell.
                    const hostCell = closestElement(table.parentElement, 'td');
                    const childTable = item.querySelector('table');
                    if (direction === 'col' &&
                        (hostCell && tableRect.right + sizeDelta > hostCell.getBoundingClientRect().right - 5 ||
                        childTable && childTable.getBoundingClientRect().right > itemRect.right + sizeDelta - 5)) {
                        break;
                    }
                    table.style[marginProp] = newMargin + 'px';
                    item.style[sizeProp] = newSize + 'px';
                    table.style[sizeProp] = tableRect[sizeProp] + sizeDelta + 'px';
                }
                break;
            }
            case 'middle': {
                const [itemRect, neighborRect] = [item.getBoundingClientRect(), neighbor.getBoundingClientRect()];
                const [currentSize, newSize] = [itemRect[sizeProp], ev[clientPositionProp] - itemRect[positionProp]];
                const editableStyle = getComputedStyle(this.editable);
                const sizeDelta = newSize - currentSize;
                const currentNeighborSize = neighborRect[sizeProp];
                const newNeighborSize = currentNeighborSize - sizeDelta;
                const maxWidth = this.editable.clientWidth - pxToFloat(editableStyle.paddingLeft) - pxToFloat(editableStyle.paddingRight);
                const tableRect = table.getBoundingClientRect();
                if (newSize > MIN_SIZE &&
                        // prevent resizing horizontally beyond the bounds of
                        // the editable:
                        (direction === 'row' ||
                        newNeighborSize > MIN_SIZE ||
                        tableRect[sizeProp] + sizeDelta < maxWidth)) {

                    // Check if a nested table would overflow its parent cell.
                    const childTable = item.querySelector('table');
                    if (direction === 'col' &&
                        childTable && childTable.getBoundingClientRect().right > itemRect.right + sizeDelta - 5) {
                        break
                    }
                    item.style[sizeProp] = newSize + 'px';
                    if (direction === 'col') {
                        neighbor.style[sizeProp] = (newNeighborSize > MIN_SIZE ? newNeighborSize : currentNeighborSize) + 'px';
                    } else {
                        table.style[sizeProp] = tableRect[sizeProp] + sizeDelta + 'px';
                    }
                }
                break;
            }
            case 'last': {
                const itemRect = item.getBoundingClientRect();
                const sizeDelta = ev[clientPositionProp] - (itemRect[positionProp] + itemRect[sizeProp]); // todo: rephrase
                const currentSize = itemRect[sizeProp];
                const newSize = currentSize + sizeDelta;
                if ((newSize >= 0 || direction === 'row') && newSize > MIN_SIZE) {
                    const tableRect = table.getBoundingClientRect();
                    // Check if a nested table would overflow its parent cell.
                    const hostCell = closestElement(table.parentElement, 'td');
                    const childTable = item.querySelector('table');
                    if (direction === 'col' &&
                        (hostCell && tableRect.right + sizeDelta > hostCell.getBoundingClientRect().right - 5 ||
                        childTable && childTable.getBoundingClientRect().right > itemRect.right + sizeDelta - 5)) {
                        break
                    }
                    table.style[sizeProp] = tableRect[sizeProp] + sizeDelta + 'px';
                    item.style[sizeProp] = newSize + 'px';
                }
                break;
            }
        }
    }
    /**
     * Show/hide and position the table row/column manipulation UI.
     *
     * @private
     * @param {HTMLTableRowElement} [row=false]
     * @param {HTMLTableCellElement} [column=false]
     */
    _toggleTableUi(row=false, column=false) {
        if (row) {
            this._rowUi.style.visibility = 'visible';
            this._rowUiTarget = row;
            this._positionTableUi(row);
        } else {
            this._rowUi.style.visibility = 'hidden';
        }
        if (column) {
            this._columnUi.style.visibility = 'visible';
            this._columnUiTarget = column;
            this._positionTableUi(column);
        } else {
            this._columnUi.style.visibility = 'hidden';
        }
        if (row || column) {
            const table = closestElement(row || column, 'table');
            table && table.addEventListener('mouseleave', () => this._toggleTableUi(), { once: true });
        }
    }
    /**
     * Position the table row/column tools (depending on whether a row or a cell
     * is passed as argument).
     *
     * @private
     * @param {HTMLTableRowElement|HTMLTableCellElement} element
     */
    _positionTableUi(element) {
        const isRow = element.nodeName === 'TR';
        const ui = isRow ? this._rowUi : this._columnUi;
        const elementRect = element.getBoundingClientRect();
        const tableRect = closestElement(element, 'table').getBoundingClientRect();
        const wrappedUi = ui.firstElementChild;
        const togglerRect = ui.querySelector('.o_table_ui_menu_toggler').getBoundingClientRect();
        const props = {
            xy: {left: 'x', top: 'y'},
            size: {left: 'width', top: 'height'}
        };

        const side1 = isRow ? 'left' : 'top';
        ui.style[side1] = (isRow ? elementRect : tableRect)[props.xy[side1]] - togglerRect[props.size[side1]] + 'px';
        wrappedUi.style[side1] = (togglerRect[props.size[side1]] / 2) + 'px';
        ui.style[props.size[side1]] = togglerRect[props.size[side1]] + 'px';

        const side2 = isRow ? 'top' : 'left';
        ui.style[side2] = elementRect[props.xy[side2]] + 'px';
        wrappedUi.style[side2] = (elementRect[props.size[side2]] / 2) - (togglerRect[props.size[side2]] / 2) + 'px';
        ui.style[props.size[side2]] = elementRect[props.size[side2]] + 'px';
    }

    // HISTORY
    // =======

    /**
     * @private
     * @returns {Object}
     */
    _computeHistorySelection() {
        const sel = this.document.getSelection();
        if (!(sel && sel.anchorNode)) {
            return this._latestComputedSelection;
        }
        this._latestComputedSelection = {
            anchorNode: sel.anchorNode,
            anchorOffset: sel.anchorOffset,
            focusNode: sel.focusNode,
            focusOffset: sel.focusOffset,
        };
        if (this.isSelectionInEditable(sel)) {
            this._latestComputedSelectionInEditable = this._latestComputedSelection;
        }
        return this._latestComputedSelection;
    }
    /**
     * @private
     * @param {boolean} [useCache=false]
     */
    _recordHistorySelection(useCache = false) {
        this._currentStep.selection =
            serializeSelection(
                useCache ? this._latestComputedSelection : this._computeHistorySelection(),
            ) || {};
    }
    /**
     * Return true if the latest computed selection was inside an empty inline tag
     *
     * @private
     * @return {boolean}
     */
    _isLatestComputedSelectionInsideEmptyInlineTag() {
        if (!this._latestComputedSelection) {
            return false;
        }
        const anchorNode = this._latestComputedSelection.anchorNode;
        const focusNode = this._latestComputedSelection.focusNode;
        const parentTextContent = anchorNode.parentElement? anchorNode.parentElement.textContent : null;
        return anchorNode === focusNode && (parentTextContent === '' || parentTextContent === '\u200B')
    }
    /**
     * Get the step index in the history to undo.
     * Return -1 if no undo index can be found.
     */
    _getNextUndoIndex() {
        // Go back to first step that can be undone ("redo" or undefined).
        for (let index = this._historySteps.length - 1; index >= 0; index--) {
            if (
                this._historySteps[index] &&
                this._historySteps[index].clientId === this._collabClientId
            ) {
                const state = this._historyStepsStates.get(this._historySteps[index].id);
                if (state === 'redo' || !state) {
                    return index;
                }
            }
        }
        // There is no steps left to be undone, return an index that does not
        // point to any step
        return -1;
    }
    /**
     * Get the step index in the history to redo.
     * Return -1 if no redo index can be found.
     */
    _getNextRedoIndex() {
        // We cannot redo more than what is consumed.
        // Check if we have no more "consumed" than "redo" until we get to an
        // "undo"
        let totalConsumed = 0;
        for (let index = this._historySteps.length - 1; index >= 0; index--) {
            if (
                this._historySteps[index] &&
                this._historySteps[index].clientId === this._collabClientId
            ) {
                const state = this._historyStepsStates.get(this._historySteps[index].id);
                switch (state) {
                    case 'undo':
                        return totalConsumed <= 0 ? index : -1;
                    case 'redo':
                        totalConsumed -= 1;
                        break;
                    case 'consumed':
                        totalConsumed += 1;
                        break;
                    default:
                        return -1;
                }
            }
        }
        return -1;
    }
    historyRevertUntil (toStepIndex) {
        const lastStep = this._currentStep;
        this.historyRevert(lastStep);
        let stepIndex = this._historySteps.length - 1;
        while (stepIndex > toStepIndex) {
            const step = this._historySteps[stepIndex];
            const stepState = this._historyStepsStates.get(step.id);
            if (step.clientId === this._collabClientId && stepState !== 'consumed') {
                this.historyRevert(this._historySteps[stepIndex]);
                this._historyStepsStates.set(''+step.id, 'consumed');
            }
            stepIndex--;
        }
    }

    // TOOLBAR
    // =======

    toolbarHide() {
        this._updateToolbar(false);
    }
    toolbarShow() {
        this._updateToolbar(true);
    }
    /**
     * @private
     * @param {boolean} [show]
     */
    _updateToolbar(show) {
        if (!this.toolbar) {
            return;
        }
        if (!this.autohideToolbar && this.toolbar.style.visibility !== 'visible') {
            this.toolbar.style.visibility = 'visible';
        }

        const sel = this.document.getSelection();
        if (!hasTableSelection(this.editable)) {
            if (this.editable.classList.contains('o_col_resize') || this.editable.classList.contains('o_row_resize')) {
                show = false;
            }
            if (!sel.anchorNode) {
                show = false;
            } else {
                const selAncestors = [sel.anchorNode, ...ancestors(sel.anchorNode, this.editable)];
                const isInStars = selAncestors.some(node => node.classList && node.classList.contains('o_stars'));
                if (isInStars) {
                    show = false;
                }
            }
        }
        if (this.autohideToolbar && !this.toolbar.contains(sel.anchorNode)) {
            if (!this.isMobile) {
                if (show !== undefined) {
                    this.toolbar.style.visibility = show ? 'visible' : 'hidden';
                }
                if (show === false) {
                    return;
                }
            }
        }
        if (!this.isSelectionInEditable(sel)) {
            return;
        }
        const paragraphDropdownButton = this.toolbar.querySelector('#paragraphDropdownButton');
        if (paragraphDropdownButton) {
            for (const commandState of [
                'justifyLeft',
                'justifyRight',
                'justifyCenter',
                'justifyFull',
            ]) {
                const button = this.toolbar.querySelector('#' + commandState);
                const direction = commandState === 'justifyFull'
                    ? 'justify' : commandState.replace('justify', '').toLowerCase();
                let isStateTrue = false;
                const link = sel.anchorNode && closestElement(sel.anchorNode, 'a');
                const linkBlock = link && closestBlock(link);
                if (linkBlock) {
                    // We don't support links with a width that is larger than
                    // their contents so an alignment within the link is not
                    // visible. Since the editor applies alignments to a node's
                    // closest block, we show the alignment of the link's
                    // closest block.
                    const alignment = getComputedStyle(linkBlock).textAlign;
                    isStateTrue = alignment === direction;
                } else {
                    isStateTrue = this.document.queryCommandState(commandState)
                }
                button.classList.toggle('active', isStateTrue);
                const newClass = `fa-align-${direction}`;
                paragraphDropdownButton.classList.toggle(newClass, isStateTrue);
            }
        }
        if (sel.rangeCount) {
            const closestStartContainer = closestElement(sel.getRangeAt(0).startContainer, '*');
            const selectionStartStyle = getComputedStyle(closestStartContainer);

            // queryCommandState does not take stylesheets into account
            for (const format of ['bold', 'italic', 'underline', 'strikeThrough', 'switchDirection']) {
                const formatButton = this.toolbar.querySelector(`#${format.toLowerCase()}`);
                if (formatButton) {
                    formatButton.classList.toggle('active', isSelectionFormat(this.editable, format));
                }
            }

            const fontSizeValue = this.toolbar.querySelector('#fontSizeCurrentValue');
            if (fontSizeValue) {
                fontSizeValue.textContent = /\d+/.exec(selectionStartStyle.fontSize).pop();
            }
            const table = getInSelection(this.document, 'table');
            const toolbarButton = this.toolbar.querySelector('.toolbar-edit-table');
            if (toolbarButton) {
                this.toolbar.querySelector('.toolbar-edit-table').style.display = table
                    ? 'block'
                    : 'none';
            }
        }
        this.updateColorpickerLabels();
        const listUIClasses = {UL: 'fa-list-ul', OL: 'fa-list-ol', CL: 'fa-tasks'};
        const block = closestBlock(sel.anchorNode);
        let activeLabel = undefined;
        for (const [style, tag, isList] of [
            ['paragraph', 'P', false],
            ['pre', 'PRE', false],
            ['heading1', 'H1', false],
            ['heading2', 'H2', false],
            ['heading3', 'H3', false],
            ['heading4', 'H4', false],
            ['heading5', 'H5', false],
            ['heading6', 'H6', false],
            ['blockquote', 'BLOCKQUOTE', false],
            ['unordered', 'UL', true],
            ['ordered', 'OL', true],
            ['checklist', 'CL', true],
        ]) {
            const button = this.toolbar.querySelector('#' + style);
            if (button && !block) {
                button.classList.toggle('active', false);
            } else if (button) {
                const isActive = isList
                    ? block.tagName === 'LI' && getListMode(block.parentElement) === tag
                    : block.tagName === tag;
                button.classList.toggle('active', isActive);

                if (!isList && isActive) {
                    activeLabel = button.textContent;
                }
            }
        }
        if (block) {
            const listMode = getListMode(block.parentElement);
            const listDropdownButton = this.toolbar.querySelector('#listDropdownButton');
            if (listDropdownButton) {
                if (listMode) {
                    listDropdownButton.classList.remove('fa-list-ul', 'fa-list-ol', 'fa-tasks');
                    listDropdownButton.classList.add(listUIClasses[listMode]);
                }
                listDropdownButton.closest('button').classList.toggle('active', block.tagName === 'LI');
            }
        }

        const styleSection = this.toolbar.querySelector('#style');
        if (styleSection) {
            if (!activeLabel) {
                // If no element from the text style dropdown was marked as active,
                // mark the paragraph one as active and use its label.
                const firstButtonEl = styleSection.querySelector('#paragraph');
                firstButtonEl.classList.add('active');
                activeLabel = firstButtonEl.textContent;
            }
            styleSection.querySelector('button span').textContent = activeLabel;
        }

        const linkNode = getInSelection(this.document, 'a');
        const linkButton = this.toolbar.querySelector('#createLink');
        linkButton && linkButton.classList.toggle('active', !!linkNode);
        const unlinkButton = this.toolbar.querySelector('#unlink');
        unlinkButton && unlinkButton.classList.toggle('d-none', !linkNode);
        const undoButton = this.toolbar.querySelector('#undo');
        undoButton && undoButton.classList.toggle('disabled', !this.historyCanUndo());
        const redoButton = this.toolbar.querySelector('#redo');
        redoButton && redoButton.classList.toggle('disabled', !this.historyCanRedo());
        if (this.autohideToolbar && !this.isMobile && !this.toolbar.contains(sel.anchorNode)) {
            this._positionToolbar();
        }
    }
    updateToolbarPosition() {
        if (
            this.autohideToolbar &&
            !this.isMobile &&
            getComputedStyle(this.toolbar).visibility === 'visible'
        ) {
            this._positionToolbar();
        }
    }
    _positionToolbar() {
        const OFFSET = 10;
        let isBottom = false;
        this.toolbar.classList.toggle('toolbar-bottom', false);
        this.toolbar.style.maxWidth = window.innerWidth - OFFSET * 2 + 'px';
        const sel = this.document.getSelection();
        const range = sel.getRangeAt(0);
        const isSelForward =
            sel.anchorNode === range.startContainer && sel.anchorOffset === range.startOffset;
        const startRect = range.startContainer.getBoundingClientRect && range.startContainer.getBoundingClientRect();
        const selRect = range.getBoundingClientRect();
        // In some undetermined circumstance in chrome, the selection rect is
        // wrongly defined and result with all the values for x, y, width, and
        // height to be 0. In that case, use the rect of the startContainer if
        // possible.
        const isSelectionPotentiallyBugged = [selRect.x, selRect.y, selRect.width, selRect.height].every( x => x === 0 );
        let correctedSelectionRect = isSelectionPotentiallyBugged && startRect ? startRect : selRect;
        const selAncestors = [sel.anchorNode, ...ancestors(sel.anchorNode, this.editable)];
        // If a table is selected, we want to position the toolbar in function
        // of the table, rather than follow the DOM selection.
        const selectedTable = selAncestors.find(node => node.classList && node.classList.contains('o_selected_table'));
        if (selectedTable) {
            correctedSelectionRect = selectedTable.getBoundingClientRect();
        }
        const toolbarWidth = this.toolbar.offsetWidth;
        const toolbarHeight = this.toolbar.offsetHeight;
        const editorRect = this.editable.getBoundingClientRect();
        const parentContextRect = this.options.getContextFromParentRect();
        const editorTopPos = Math.max(0, editorRect.top);
        const scrollX = this.document.defaultView.scrollX;
        const scrollY = this.document.defaultView.scrollY;

        // Get left position.
        let left = correctedSelectionRect.left + OFFSET;
        // Ensure the toolbar doesn't overflow the editor on the left.
        left = Math.max(OFFSET, left);
        // Ensure the toolbar doesn't overflow the editor on the right.
        left = Math.min(window.innerWidth - OFFSET - toolbarWidth, left);
        // Offset left to compensate for parent context position (eg. Iframe).
        left += parentContextRect.left;
        this.toolbar.style.left = scrollX + left + 'px';

        // Get top position.
        let top = correctedSelectionRect.top - toolbarHeight - OFFSET;
        // Ensure the toolbar doesn't overflow the editor on the top.
        if (top < editorTopPos) {
            // Position the toolbar below the selection.
            top = correctedSelectionRect.bottom + OFFSET;
            isBottom = true;
        }
        // Ensure the toolbar doesn't overflow the editor on the bottom.
        top = Math.min(window.innerHeight - OFFSET - toolbarHeight, top);
        // Offset top to compensate for parent context position (eg. Iframe).
        top += parentContextRect.top;
        this.toolbar.style.top = scrollY + top + 'px';

        // Position the arrow.
        let arrowLeftPos = (isSelForward && !isSelectionPotentiallyBugged ? correctedSelectionRect.right : correctedSelectionRect.left) - left - OFFSET;
        // Ensure the arrow doesn't overflow the toolbar on the left.
        arrowLeftPos = Math.max(OFFSET, arrowLeftPos);
        // Ensure the arrow doesn't overflow the toolbar on the right.
        arrowLeftPos = Math.min(toolbarWidth - OFFSET - 20, arrowLeftPos);
        this.toolbar.style.setProperty('--arrow-left-pos', arrowLeftPos + 'px');
        if (isBottom) {
            this.toolbar.classList.toggle('toolbar-bottom', true);
            this.toolbar.style.setProperty('--arrow-top-pos', -17 + 'px');
        } else {
            this.toolbar.style.setProperty('--arrow-top-pos', toolbarHeight - 3 + 'px');
        }
    }

    // PASTING / DROPPING

    /**
     * Prepare clipboard data (text/html) for safe pasting into the editor.
     *
     * @private
     * @param {string} clipboardData
     * @returns {Element}
     */
    _prepareClipboardData(clipboardData) {
        const container = document.createElement('fake-container');
        container.append(parseHTML(clipboardData));

        for (const tableElement of container.querySelectorAll('table')) {
            tableElement.classList.add('table', 'table-bordered', 'o_table');
        }

        for (const child of [...container.childNodes]) {
            this._cleanForPaste(child);
        }
        // Force inline nodes at the root of the container into separate P
        // elements. This is a tradeoff to ensure some features that rely on
        // nodes having a parent (e.g. convert to list, title, etc.) can work
        // properly on such nodes without having to actually handle that
        // particular case in all of those functions. In fact, this case cannot
        // happen on a new document created using this editor, but will happen
        // instantly when editing a document that was created from Etherpad.
        const fragment = document.createDocumentFragment();
        let p = document.createElement('p');
        for (const child of [...container.childNodes]) {
            if (isBlock(child)) {
                if (p.childNodes.length > 0) {
                    fragment.appendChild(p);
                    p = document.createElement('p');
                }
                fragment.appendChild(child);
            } else {
                p.appendChild(child);
            }

            if (p.childNodes.length > 0) {
                fragment.appendChild(p);
            }
        }
        return fragment;
    }
    /**
     * Clean a node for safely pasting. Cleaning an element involves unwrapping
     * its contents if it's an illegal (blacklisted or not whitelisted) element,
     * or removing its illegal attributes and classes.
     *
     * @param {Node} node
     */
    _cleanForPaste(node) {
        if (!this._isWhitelisted(node) || this._isBlacklisted(node)) {
            if (!node.matches || node.matches(CLIPBOARD_BLACKLISTS.remove.join(','))) {
                node.remove();
            } else {
                // Unwrap the illegal node's contents.
                for (const unwrappedNode of unwrapContents(node)) {
                    this._cleanForPaste(unwrappedNode);
                }
            }
        } else if (node.nodeType !== Node.TEXT_NODE) {
            // Remove all illegal attributes and classes from the node, then
            // clean its children.
            for (const attribute of [...node.attributes]) {
                // Keep allowed styles on nodes with allowed tags.
                if (CLIPBOARD_WHITELISTS.styledTags.includes(node.nodeName) && attribute.name === 'style') {
                    const spanInlineStyles = attribute.value.split(';').map(x => x.trim());
                    const allowedSpanInlineStyles = spanInlineStyles.filter(rawStyle => {
                        const [styleName, styleValue] = rawStyle.split(':');
                        const style = CLIPBOARD_WHITELISTS.styles[styleName.trim()];
                        return style && !style.defaultValues.includes(styleValue.trim());
                    });
                    node.removeAttribute(attribute.name);
                    if (allowedSpanInlineStyles.length > 0) {
                        node.setAttribute(attribute.name, allowedSpanInlineStyles.join(';'));
                    } else if (['SPAN', 'FONT'].includes(node.tagName)) {
                        for (const unwrappedNode of unwrapContents(node)) {
                            this._cleanForPaste(unwrappedNode);
                        }
                    }
                } else if (!this._isWhitelisted(attribute)) {
                    node.removeAttribute(attribute.name);
                }

            }
            for (const klass of [...node.classList]) {
                if (!this._isWhitelisted(klass)) {
                    node.classList.remove(klass);
                }
            }
            for (const child of [...node.childNodes]) {
                this._cleanForPaste(child);
            }
        }
    }
    /**
     * Return true if the given attribute, class or node is whitelisted for
     * pasting, false otherwise.
     *
     * @private
     * @param {Attr | string | Node} item
     * @returns {boolean}
     */
    _isWhitelisted(item) {
        if (item instanceof Attr) {
            return CLIPBOARD_WHITELISTS.attributes.includes(item.name);
        } else if (typeof item === 'string') {
            return CLIPBOARD_WHITELISTS.classes.some(okClass =>
                okClass instanceof RegExp ? okClass.test(item) : okClass === item,
            );
        } else {
            const allowedSpanStyles = Object.keys(CLIPBOARD_WHITELISTS.styles).map(s => `span[style*="${s}"]`);
            return (
                item.nodeType === Node.TEXT_NODE ||
                (
                    item.matches &&
                    item.matches([...CLIPBOARD_WHITELISTS.nodes, ...allowedSpanStyles].join(','))
                )
            );
        }
    }
    /**
     * Return true if the given node is blacklisted for pasting, false
     * otherwise.
     *
     * @private
     * @param {Node} node
     * @returns {boolean}
     */
    _isBlacklisted(node) {
        return (
            node.nodeType !== Node.TEXT_NODE &&
            node.matches([].concat(...Object.values(CLIPBOARD_BLACKLISTS)).join(','))
        );
    }
    _safeSetAttribute(node, attributeName, attributeValue) {
        const parent = node.parentNode;
        const next = node.nextSibling;
        this.observerFlush();
        node.remove();
        this.observer.takeRecords();
        node.setAttribute(attributeName, attributeValue);
        this.observerFlush();
        DOMPurify.sanitize(node, { IN_PLACE: true });
        if (next) {
            next.before(node);
        } else if (parent) {
            parent.append(node);
        }
        this.observer.takeRecords();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onBeforeInput(ev) {
        this._lastBeforeInputType = ev.inputType;
    }

    /**
     * If backspace/delete input, rollback the operation and handle the
     * operation ourself. Needed for mobile, used for desktop for consistency.
     *
     * @private
     */
    _onInput(ev) {
        // See if the Powerbox should be opened. If so, it will open at the end.
        const newSelection = this.document.getSelection();
        const shouldOpenPowerbox = newSelection.isCollapsed && newSelection.rangeCount &&
            ev.data === '/' && this.powerbox && !this.powerbox.isOpen &&
            (!this.options.getPowerboxElement || !!this.options.getPowerboxElement());
        if (shouldOpenPowerbox) {
            // Undo input '/'.
            this._powerboxBeforeStepIndex = this._historySteps.length - 1;
        }
        // Record the selection position that was computed on keydown or before
        // contentEditable execCommand (whatever preceded the 'input' event)
        this._recordHistorySelection(true);
        const selection = this._currentStep.selection;
        const { anchorNodeOid, anchorOffset, focusNodeOid, focusOffset } = selection || {};
        const wasCollapsed =
            !selection || (focusNodeOid === anchorNodeOid && focusOffset === anchorOffset);
        // Sometimes google chrome wrongly triggers an input event with `data`
        // being `null` on `deleteContentForward` `insertParagraph`. Luckily,
        // chrome provide the proper signal with the event `beforeinput`.
        const isChromeDeleteforward =
            ev.inputType === 'insertText' &&
            ev.data === null &&
            this._lastBeforeInputType === 'deleteContentForward';
        const isChromeInsertParagraph =
            ev.inputType === 'insertText' &&
            ev.data === null &&
            this._lastBeforeInputType === 'insertParagraph';
        if (this.keyboardType === KEYBOARD_TYPES.PHYSICAL || !wasCollapsed) {
            if (ev.inputType === 'deleteContentBackward') {
                this._compositionStep();
                this.historyRollback();
                ev.preventDefault();
                this._applyCommand('oDeleteBackward');
            } else if (ev.inputType === 'deleteContentForward' || isChromeDeleteforward) {
                this._compositionStep();
                this.historyRollback();
                ev.preventDefault();
                this._applyCommand('oDeleteForward');
            } else if (ev.inputType === 'insertParagraph' || isChromeInsertParagraph) {
                this._compositionStep();
                this.historyRollback();
                ev.preventDefault();
                if (this._applyCommand('oEnter') === UNBREAKABLE_ROLLBACK_CODE) {
                    const brs = this._applyCommand('oShiftEnter');
                    const anchor = brs[0].parentElement;
                    if (anchor.nodeName === 'A') {
                        if (brs.includes(anchor.firstChild)) {
                            brs.forEach(br => anchor.before(br));
                            setSelection(...rightPos(brs[brs.length - 1]));
                            this.historyStep();
                        } else if (brs.includes(anchor.lastChild)) {
                            brs.forEach(br => anchor.after(br));
                            setSelection(...rightPos(brs[0]));
                            this.historyStep();
                        }
                    }
                }
            } else if (['insertText', 'insertCompositionText'].includes(ev.inputType)) {
                // insertCompositionText, courtesy of Samsung keyboard.
                const selection = this.document.getSelection();
                // Detect that text was selected and change behavior only if it is the case,
                // since it is the only text insertion case that may cause problems.
                const wasTextSelected = anchorNodeOid !== focusNodeOid || anchorOffset !== focusOffset;
                // Unit tests events are not trusted by the browser,
                // the insertText has to be done manualy.
                const isUnitTests = !ev.isTrusted && this.testMode;
                // we cannot trust the browser to keep the selection inside empty tags.
                const latestSelectionInsideEmptyTag = this._isLatestComputedSelectionInsideEmptyInlineTag();
                if (wasTextSelected || isUnitTests || latestSelectionInsideEmptyTag) {
                    ev.preventDefault();
                    if (!isUnitTests) {
                        // First we need to undo the character inserted by the browser.
                        // Since the unit test Event is not trusted by the browser, we don't
                        // need to undo the char during the unit tests.
                        // @see https://developer.mozilla.org/en-US/docs/Web/API/Event/isTrusted
                        this._applyRawCommand('oDeleteBackward');
                    }
                    if (latestSelectionInsideEmptyTag) {
                        // Restore the selection inside the empty Element.
                        const selectionBackup = this._latestComputedSelection;
                        setSelection(selectionBackup.anchorNode, selectionBackup.anchorOffset);
                    }
                    // When the spellcheck of Safari modify text, ev.data is
                    // null and the string can be found within ev.dataTranser.
                    insertText(selection, ev.data === null ? ev.dataTransfer.getData('text/plain') : ev.data);
                    selection.collapseToEnd();
                }
                // Check for url after user insert a space so we won't transform an incomplete url.
                if (
                    ev.data &&
                    ev.data === ' ' &&
                    selection &&
                    selection.anchorNode &&
                    !closestElement(selection.anchorNode).closest('a') &&
                    selection.anchorNode.nodeType === Node.TEXT_NODE &&
                    !this.powerbox.isOpen
                ) {
                    const textSliced = selection.anchorNode.textContent.slice(0, selection.anchorOffset);
                    const textNodeSplitted = textSliced.split(/\s/);

                    // Remove added space
                    textNodeSplitted.pop();
                    const potentialUrl = textNodeSplitted.pop();
                    const lastWordMatch = potentialUrl.match(URL_REGEX_WITH_INFOS);

                    if (lastWordMatch) {
                        const matches = getUrlsInfosInString(textSliced);
                        const match = matches[matches.length - 1];
                        const cloneRange = selection.getRangeAt(0).cloneRange();
                        const range = this.document.createRange();
                        range.setStart(selection.anchorNode, match.index);
                        range.setEnd(selection.anchorNode, match.index + match.length);
                        const link = this._createLink(range.extractContents().textContent, match.url);
                        range.insertNode(link);
                        // Inserting an element into a range clears the selection in Safari
                        // Hence, use the cloned range to reselect it.
                        selection.removeAllRanges();
                        selection.addRange(cloneRange);
                    }
                    selection.collapseToEnd();
                }
                if (ev.data === '`' && !closestElement(selection.anchorNode, 'code')) {
                    // We just inserted a backtick, check if there was another
                    // one in the text.
                    const range = getDeepRange(this.editable);
                    let textNode = range.startContainer;
                    let offset = range.startOffset;
                    let sibling = textNode.previousSibling;
                    while (sibling && sibling.nodeType === Node.TEXT_NODE) {
                        offset += sibling.textContent.length;
                        sibling.textContent += textNode.textContent;
                        textNode.remove();
                        textNode = sibling;
                        sibling = textNode.previousSibling;
                    }
                    sibling = textNode.nextSibling;
                    while (sibling && sibling.nodeType === Node.TEXT_NODE) {
                        textNode.textContent += sibling.textContent;
                        sibling.remove();
                        sibling = textNode.nextSibling;
                    }
                    setSelection(textNode, offset);
                    const textHasTwoTicks = /`.*`/.test(textNode.textContent);
                    if (textHasTwoTicks) {
                        this.historyStep();
                        const insertedBacktickIndex = offset - 1;
                        const textBeforeInsertedBacktick = textNode.textContent.substring(0, insertedBacktickIndex - 1);
                        let startOffset, endOffset;
                        const isClosingForward = textBeforeInsertedBacktick.includes('`');
                        if (isClosingForward) {
                            // There is a backtick before the new backtick.
                            startOffset = textBeforeInsertedBacktick.lastIndexOf('`');
                            endOffset = insertedBacktickIndex;
                        } else {
                            // There is a backtick after the new backtick.
                            const textAfterInsertedBacktick = textNode.textContent.substring(offset);
                            startOffset = insertedBacktickIndex;
                            endOffset = offset + textAfterInsertedBacktick.indexOf('`');
                        }
                        // Split around the backticks if needed so text starts
                        // and ends with a backtick.
                        if (endOffset && endOffset < textNode.textContent.length) {
                            splitTextNode(textNode, endOffset + 1, DIRECTIONS.LEFT);
                        }
                        if (startOffset) {
                            splitTextNode(textNode, startOffset);
                        }
                        // Remove ticks.
                        textNode.textContent = textNode.textContent.substring(1, textNode.textContent.length - 1);
                        // Insert code element.
                        const codeElement = this.document.createElement('code');
                        codeElement.classList.add('o_inline_code');
                        textNode.before(codeElement);
                        codeElement.append(textNode);
                        if (!codeElement.previousSibling || codeElement.previousSibling.nodeType !== Node.TEXT_NODE) {
                            codeElement.before(document.createTextNode('\u200B'));
                        }
                        if (isClosingForward) {
                            // Move selection out of code element.
                            codeElement.after(document.createTextNode('\u200B'));
                            setSelection(codeElement.nextSibling, 1);
                        } else {
                            setSelection(codeElement.firstChild, 0);
                        }
                    }
                }
                this.historyStep();
            } else {
                this.historyStep();
            }
        } else if (ev.inputType === 'insertCompositionText') {
            this._fromCompositionText = true;
        }
        if (shouldOpenPowerbox) {
            this._isPowerboxOpenOnInput = true;
            this.powerbox.open();
        }
    }

    _onClipboardCut(clipboardEvent) {
        this._onClipboardCopy(clipboardEvent);
        this._recordHistorySelection();
        this.deleteRange();
        this.historyStep();
    }
    _onClipboardCopy(clipboardEvent) {
        if (!this.isSelectionInEditable()) {
            return;
        }
        clipboardEvent.preventDefault();
        const selection = this.document.getSelection();
        const range = selection.getRangeAt(0);
        let rangeContent = range.cloneContents();
        if (!rangeContent.hasChildNodes()) {
            return;
        }
        // Repair the copied range.
        if (rangeContent.firstChild.nodeName === 'LI') {
            const list = range.commonAncestorContainer.cloneNode();
            list.replaceChildren(...rangeContent.childNodes);
            rangeContent = list;
        }
        if (rangeContent.firstChild.nodeName === 'TR' || rangeContent.firstChild.nodeName === 'TD') {
            // We enter this case only if selection is within single table.
            const table = closestElement(range.commonAncestorContainer, 'table');
            const tableClone = table.cloneNode(true);
            // A table is considered fully selected if it is nested inside a
            // cell that is itself selected, or if all its own cells are
            // selected.
            const isTableFullySelected =
                table.parentElement && !!closestElement(table.parentElement, 'td.o_selected_td') ||
                [...table.querySelectorAll('td')]
                    .filter(td => closestElement(td, 'table') === table)
                    .every(td => td.classList.contains('o_selected_td'));
            if (!isTableFullySelected) {
                for (const td of tableClone.querySelectorAll('td:not(.o_selected_td)')) {
                    if (closestElement(td, 'table') === tableClone) { // ignore nested
                        td.remove();
                    }
                }
                for (const tr of tableClone.querySelectorAll('tr:not(:has(td))')) {
                    if (closestElement(tr, 'table') === tableClone) { // ignore nested
                        tr.remove();
                    }
                }
            }
            // If it is fully selected, clone the whole table rather than
            // just its rows.
            rangeContent = tableClone;
        }
        if (rangeContent.firstChild.nodeName === 'TABLE') {
            // Make sure the full leading table is copied.
            rangeContent.firstChild.after(closestElement(range.startContainer, 'table').cloneNode(true));
            rangeContent.firstChild.remove();
        }
        if (rangeContent.lastChild.nodeName === 'TABLE') {
            // Make sure the full trailing table is copied.
            rangeContent.lastChild.before(closestElement(range.endContainer, 'table').cloneNode(true));
            rangeContent.lastChild.remove();
        }

        const dataHtmlElement = document.createElement('data');
        dataHtmlElement.append(rangeContent);
        const odooHtml = dataHtmlElement.innerHTML;
        const odooText = selection.toString();
        clipboardEvent.clipboardData.setData('text/plain', odooText);
        clipboardEvent.clipboardData.setData('text/html', odooHtml);
        clipboardEvent.clipboardData.setData('text/odoo-editor', odooHtml);
    }
    /**
     * @private
     */
    _onKeyDown(ev) {
        this.keyboardType =
            ev.key === 'Unidentified' ? KEYBOARD_TYPES.VIRTUAL : KEYBOARD_TYPES.PHYSICAL;
        this._currentKeyPress = ev.key;
        // If the pressed key has a printed representation, the returned value
        // is a non-empty Unicode character string containing the printable
        // representation of the key. In this case, call `deleteRange` before
        // inserting the printed representation of the character.
        if (/^.$/u.test(ev.key) && !ev.ctrlKey && !ev.metaKey && (isMacOS() || !ev.altKey)) {
            const selection = this.document.getSelection();
            if (selection && !selection.isCollapsed) {
                this.deleteRange(selection);
            }
        }
        if (ev.key === 'Backspace') {
            // backspace
            const selection = this.document.getSelection();
            if (!ev.ctrlKey && !ev.metaKey) {
                if (selection.isCollapsed) {
                    // We need to hijack it because firefox doesn't trigger a
                    // deleteBackward input event with a collapsed selection in
                    // front of a contentEditable="false" (eg: font awesome).
                    ev.preventDefault();
                    this._applyCommand('oDeleteBackward');
                }
            } else if (selection.isCollapsed && selection.anchorNode) {
                const anchor = (selection.anchorNode.nodeType !== Node.TEXT_NODE && selection.anchorOffset) ?
                    selection.anchorNode[selection.anchorOffset] : selection.anchorNode;
                const element = closestBlock(anchor);
                if (isEmptyBlock(element) && element.parentElement.children.length === 1) {
                    // Prevent removing a <p> if it is the last element of its
                    // parent.
                    ev.preventDefault();
                    if (element.tagName !== 'P') {
                        // Replace an empty block which is not a <p> by a <p>
                        const paragraph = this.document.createElement('P');
                        const br = this.document.createElement('BR');
                        paragraph.append(br);
                        element.before(paragraph);
                        const result = this._protect(() => element.remove());
                        if (result !== UNBREAKABLE_ROLLBACK_CODE && result !== UNREMOVABLE_ROLLBACK_CODE) {
                            setCursorStart(paragraph);
                            this.historyStep();
                        }
                    }
                }
            }
        } else if (ev.key === 'Tab') {
            // Tab
            const tabHtml = '<span class="oe-tabs" contenteditable="false">\u0009</span>\u200B';
            const sel = this.document.getSelection();
            if (closestElement(sel.anchorNode, 'table')) {
                this._onTabulationInTable(ev);
            } else if (!ev.shiftKey && sel.isCollapsed && !closestElement(sel.anchorNode, 'li')) {
                // Indent text (collapsed selection).
                this.execCommand('insert', parseHTML(tabHtml));
            } else {
                // Indent/outdent selection.
                // Split traversed nodes into list items and the rest.
                const listItems = new Set();
                const nonListItems = new Set();
                for (const node of getTraversedNodes(this.editable)) {
                    const closestLi = closestElement(node, 'li');
                    const target = closestLi || node;
                    if (!(target.querySelector && target.querySelector('li'))) {
                        if (closestLi) {
                            listItems.add(closestLi);
                        } else {
                            nonListItems.add(node);
                        }
                    }
                }

                const restore = preserveCursor(this.document);

                // Indent/outdent list items.
                for (const listItem of listItems) {
                    if (ev.shiftKey) {
                        listItem.oShiftTab(0);
                    } else {
                        listItem.oTab(0);
                    }
                }

                // Indent/outdent the rest.
                if (ev.shiftKey) {
                    const editorTabs = new Set(
                        [...nonListItems].map(node => {
                            const block = closestBlock(node);
                            if (block && isEditorTab(block.firstElementChild)) {
                                return block.firstElementChild;
                            }
                        }).filter(node => (
                            // Filter out tabs preceded by visible text.
                            node && !getAdjacentPreviousSiblings(node).some(sibling => (
                                sibling.nodeType === Node.TEXT_NODE && !/^[\u200B\s]*$/.test(sibling.textContent)
                            ))
                    )));
                    for (const tab of editorTabs) {
                        let { anchorNode, anchorOffset, focusNode, focusOffset } = sel;
                        const updateAnchor = anchorNode === tab.nextSibling;
                        const updateFocus = focusNode === tab.nextSibling;
                        let zwsRemoved = 0;
                        while (tab.nextSibling && tab.nextSibling.nodeType === Node.TEXT_NODE && tab.nextSibling.textContent.startsWith('\u200B')) {
                            splitTextNode(tab.nextSibling, 1, DIRECTIONS.LEFT);
                            tab.nextSibling.remove();
                            zwsRemoved++;
                        }
                        if (updateAnchor || updateFocus) {
                            setSelection(
                                updateAnchor ? tab.nextSibling : anchorNode,
                                updateAnchor ? Math.max(0, anchorOffset - zwsRemoved) : anchorOffset,
                                updateFocus ? tab.nextSibling : focusNode,
                                updateFocus ? Math.max(0, focusOffset - zwsRemoved) : focusOffset
                            );
                        }
                        tab.remove();
                    };
                } else {
                    const tab = parseHTML(tabHtml);
                    for (const block of new Set([...nonListItems].map(node => closestBlock(node)).filter(node => node))) {
                        block.prepend(tab.cloneNode(true));
                    }
                    restore();
                }
                this.historyStep();
            }
            ev.preventDefault();
            ev.stopPropagation();
        } else if (ev.shiftKey && ev.key === "Enter") {
            ev.preventDefault();
            this._applyCommand('oShiftEnter');
        } else if (IS_KEYBOARD_EVENT_UNDO(ev)) {
            // Ctrl-Z
            ev.preventDefault();
            ev.stopPropagation();
            this.historyUndo();
        } else if (IS_KEYBOARD_EVENT_REDO(ev)) {
            // Ctrl-Y
            ev.preventDefault();
            ev.stopPropagation();
            this.historyRedo();
        } else if (IS_KEYBOARD_EVENT_BOLD(ev)) {
            // Ctrl-B
            ev.preventDefault();
            ev.stopPropagation();
            this.execCommand('bold');
        } else if (IS_KEYBOARD_EVENT_ITALIC(ev)) {
            // Ctrl-I
            ev.preventDefault();
            ev.stopPropagation();
            this.execCommand('italic');
        } else if (IS_KEYBOARD_EVENT_UNDERLINE(ev)) {
            // Ctrl-U
            ev.preventDefault();
            ev.stopPropagation();
            this.execCommand('underline');
        } else if (IS_KEYBOARD_EVENT_STRIKETHROUGH(ev)) {
            // Ctrl-5 / Ctrl-shift-(
            ev.preventDefault();
            ev.stopPropagation();
            this.execCommand('strikeThrough');
        } else if (IS_KEYBOARD_EVENT_LEFT_ARROW(ev)) {
            getDeepRange(this.editable);
            const selection = this.document.getSelection();
            // Find previous character.
            let { focusNode, focusOffset } = selection;
            let previousCharacter = focusOffset > 0 && focusNode.textContent[focusOffset - 1];
            if (!previousCharacter) {
                focusNode = previousLeaf(focusNode);
                focusOffset = nodeSize(focusNode);
                previousCharacter = focusNode.textContent[focusOffset - 1];
            }
            // Move selection if previous character is zero-width space
            if (previousCharacter === '\u200B') {
                focusOffset -= 1;
                while (focusNode && (focusOffset < 0 || !focusNode.textContent[focusOffset])) {
                    focusNode = nextLeaf(focusNode);
                    focusOffset = focusNode && nodeSize(focusNode);
                }
                const startContainer = ev.shiftKey ? selection.anchorNode : focusNode;
                const startOffset = ev.shiftKey ? selection.anchorOffset : focusOffset;
                setSelection(startContainer, startOffset, focusNode, focusOffset);
            }
        } else if (IS_KEYBOARD_EVENT_RIGHT_ARROW(ev)) {
            getDeepRange(this.editable);
            const selection = this.document.getSelection();
            // Find next character.
            let { focusNode, focusOffset } = selection;
            let nextCharacter = focusNode.textContent[focusOffset];
            if (!nextCharacter) {
                focusNode = nextLeaf(focusNode);
                focusOffset = 0;
                nextCharacter = focusNode.textContent[focusOffset];
            }
            // Move selection if next character is zero-width space
            if (nextCharacter === '\u200B') {
                focusOffset += 1;
                let newFocusNode = focusNode;
                while (newFocusNode && (!newFocusNode.textContent[focusOffset] || !closestElement(newFocusNode).isContentEditable)) {
                    newFocusNode = nextLeaf(newFocusNode);
                    focusOffset = 0;
                }
                if (!focusOffset && closestBlock(focusNode) !== closestBlock(newFocusNode)) {
                    newFocusNode = focusNode; // Do not move selection to next block.
                    focusOffset = nodeSize(focusNode);
                }
                const startContainer = ev.shiftKey ? selection.anchorNode : newFocusNode;
                const startOffset = ev.shiftKey ? selection.anchorOffset : focusOffset;
                setSelection(startContainer, startOffset, newFocusNode, focusOffset);
            }
        }
    }
    /**
     * @private
     */
    _onSelectionChange() {
        const currentKeyPress = this._currentKeyPress;
        delete this._currentKeyPress;
        const selection = this.document.getSelection();
        if (!selection) {
            // Because the `selectionchange` event is async, the selection can
            // be null if the node has been removed between the moment the
            // selection was moved and the moment the event is triggered.
            return;
        }
        const anchorNode = selection.anchorNode;
        // Correct cursor if at editable root.
        if (
            selection.isCollapsed &&
            anchorNode === this.editable &&
            !this.options.allowInlineAtRoot
        ) {
            this._fixSelectionOnEditableRoot(selection, currentKeyPress);
            // The _onSelectionChange handler is going to be triggered again.
            return;
        }
        let appliedCustomSelection = false;
        if (selection.rangeCount && selection.getRangeAt(0)) {
            appliedCustomSelection = this._handleSelectionInTable();
            if (this.options.onCollaborativeSelectionChange) {
                this.options.onCollaborativeSelectionChange(this.getCurrentCollaborativeSelection());
            }
        }
        const isSelectionInEditable = this.isSelectionInEditable(selection);
        if (!appliedCustomSelection) {
            this._updateToolbar(!selection.isCollapsed && isSelectionInEditable);
        }
        if (!isSelectionInEditable) {
            return;
        }
        // When CTRL+A in the editor, sometimes the browser use the editable
        // element as an anchor & focus node. This is an issue for the commands
        // and the toolbar so we need to fix the selection to be based on the
        // editable children. Calling `getDeepRange` ensure the selection is
        // limited to the editable.
        if (
            selection.anchorNode === this.editable &&
            selection.focusNode === this.editable &&
            selection.anchorOffset === 0 &&
            selection.focusOffset === [...this.editable.childNodes].length
        ) {
            getDeepRange(this.editable, {select: true});
            // The selection is changed in `getDeepRange` and will therefore
            // re-trigger the _onSelectionChange.
            return;
        }

        // Compute the current selection on selectionchange but do not record it. Leave
        // that to the command execution or the 'input' event handler.
        this._computeHistorySelection();

        if (this._currentMouseState === 'mouseup') {
            this._fixFontAwesomeSelection();
        }
    }

    /**
     * Returns true if the current selection is inside the editable.
     *
     * @param {Object} [selection]
     * @returns {boolean}
     */
    isSelectionInEditable(selection) {
        selection = selection || this.document.getSelection();
        if (selection && selection.anchorNode && selection.focusNode) {
            const anchorElement = closestElement(selection.anchorNode);
            const focusElement = closestElement(selection.focusNode);
            return anchorElement && anchorElement.isContentEditable && focusElement && focusElement.isContentEditable &&
                this.editable.contains(selection.anchorNode) && this.editable.contains(selection.focusNode);
        } else {
            return false;
        }
    }
    /**
     * Returns true if the current selection is in at least one block Element
     * relative to the current contentEditable root.
     *
     * @returns {boolean}
     */
    isSelectionInBlockRoot() {
        const selection = this.document.getSelection();
        let selectionInBlockRoot;
        let currentNode = closestElement(selection.anchorNode);
        while (
            !currentNode.classList.contains('o_editable') &&
            !currentNode.classList.contains('odoo-editor-editable') &&
            !selectionInBlockRoot
            ) {
            selectionInBlockRoot = isBlock(currentNode);
            currentNode = currentNode.parentElement;
        }
        return !!selectionInBlockRoot;
    }

    /**
     * @private
     */
    _compositionStep() {
        if (this._fromCompositionText) {
            this._fromCompositionText = false;
            this.sanitize();
            this.historyStep();
        }
    }

    /**
     * Returns true if the current selection content is only one ZWS
     *
     * @private
     * @param {Object} selection
     * @returns {boolean}
     */
    _isSelectionOnlyZws(selection) {
        let range = selection.getRangeAt(0);
        if (selection.isCollapsed || !range) {
            return false;
        }
        return range.cloneContents().textContent === '\u200B';
    }

    getCurrentCollaborativeSelection() {
        const selection = this._latestComputedSelection || this._computeHistorySelection();
        return {
            selection: selection ? serializeSelection(selection) : {
                anchorNodeOid: undefined,
                anchorOffset: undefined,
                focusNodeOid: undefined,
                focusOffset: undefined,
            },
            color: this._collabSelectionColor,
            clientId: this._collabClientId,
            clientAvatarUrl: this._collabClientAvatarUrl,
        };
    }

    clean() {
        this.observerUnactive();
        this.resetContenteditableLink();
        this.cleanForSave();
        this.observerActive();
    }

    /**
     * Initialize the provided element to be ready for edition.
     */
    initElementForEdition(element = this.editable) {
        // Detect if the editable base element contain orphan inline nodes. If
        // so we transform the base element HTML to put those orphans inside
        // `<p>` containers.
        const orphanInlineChildNodes = [...element.childNodes].find(
            (n) => !isBlock(n) && (n.nodeType === Node.ELEMENT_NODE || n.textContent.trim() !== "")
        );
        if (orphanInlineChildNodes && !this.options.allowInlineAtRoot) {
            const childNodes = [...element.childNodes];
            const tempEl = document.createElement('temp-container');
            let currentP = document.createElement('p');
            currentP.style.marginBottom = '0';
            do {
                const node = childNodes.shift();
                const nodeIsBlock = isBlock(node);
                const nodeIsBR = node.nodeName === 'BR';
                // Append to the P unless child is block or an unneeded BR.
                if (!(nodeIsBlock || (nodeIsBR && currentP.childNodes.length))) {
                    currentP.append(node);
                }
                // Break paragraphs on blocks and BR.
                if (nodeIsBlock || nodeIsBR || childNodes.length === 0) {
                    // Ensure we don't add an empty P or a P containing only
                    // formating spaces that should not be visible.
                    if (currentP.childNodes.length && currentP.innerHTML.trim() !== '') {
                        tempEl.append(currentP);
                    }
                    currentP = currentP.cloneNode();
                    // Append block children directly to the template.
                    if (nodeIsBlock) {
                        tempEl.append(node);
                    }
                }
            } while (childNodes.length)
            element.replaceChildren(...tempEl.childNodes);
        }

        // Flag elements with forced contenteditable=false.
        // We need the flag to be able to leave the contentEditable
        // at the end of the edition (see cleanForSave())
        for (const el of element.querySelectorAll('[contenteditable="false"]')) {
            el.setAttribute('data-oe-keep-contenteditable', '');
        }
        // Flag elements .oe-tabs contenteditable=false.
        for (const el of element.querySelectorAll('.oe-tabs')) {
            el.setAttribute('contenteditable', 'false');
        }
    }

    cleanForSave(element = this.editable) {
        for (const hint of element.querySelectorAll('.oe-hint')) {
            hint.classList.remove('oe-hint', 'oe-command-temporary-hint');
            if (hint.classList.length === 0) {
                hint.removeAttribute('class');
            }
            hint.removeAttribute('placeholder');
        }
        this._pluginCall('cleanForSave', [element]);
        // Clean the remaining ZeroWidthspaces added by the `fillEmpty` function
        // ( contain "data-oe-zws-empty-inline" attr)
        // If the element contain more than just a ZWS,
        // we remove it and clean the attribute.
        // If the element have a class,
        // we only remove the attribute to ensure we don't break some style.
        // Otherwise we remove the entire inline element.
        for (const emptyElement of element.querySelectorAll('[data-oe-zws-empty-inline]')) {
            if (isZWS(emptyElement)) {
                if (emptyElement.classList.length > 0) {
                    emptyElement.removeAttribute('data-oe-zws-empty-inline');
                } else {
                    emptyElement.remove();
                }
            } else {
                cleanZWS(emptyElement);
                emptyElement.removeAttribute('data-oe-zws-empty-inline');
            }
        }

        // Clean all protected nodes because they are not sanitized
        const protectedNodes = element.querySelectorAll('[data-oe-protected="true"]');
        for (const node of protectedNodes) {
            node.replaceChildren();
        }

        sanitize(element);

        // Remove contenteditable=false on elements
        for (const el of element.querySelectorAll('[contenteditable="false"]')) {
            if (!el.hasAttribute('data-oe-keep-contenteditable')) {
                el.removeAttribute('contenteditable');
            }
        }
        // Remove data-oe-keep-contenteditable on elements
        for (const el of element.querySelectorAll('[data-oe-keep-contenteditable]')) {
            el.removeAttribute('data-oe-keep-contenteditable');
        }

        // Remove Zero Width Spaces on Font awesome elements
        const faSelector = 'i.fa,span.fa,i.fab,span.fab,i.fad,span.fad,i.far,span.far';
        for (const el of element.querySelectorAll(faSelector)) {
            cleanZWS(el);
        }

        // Clean custom selections
        if (this.deselectTable() && hasValidSelection(this.editable)) {
            this.document.getSelection().collapseToStart();
        }
    }
    /**
     * Handle the hint preview for the Powerbox.
     * @private
     */
    _handleCommandHint() {
        const selection = this.document.getSelection();
        const anchorNode = selection.anchorNode;
        if (anchorNode && closestElement(anchorNode, '[data-oe-protected="true"]')) {
            return;
        }

        const selectors = {
            BLOCKQUOTE: this.options._t('Empty quote'),
            H1: this.options._t('Heading 1'),
            H2: this.options._t('Heading 2'),
            H3: this.options._t('Heading 3'),
            H4: this.options._t('Heading 4'),
            H5: this.options._t('Heading 5'),
            H6: this.options._t('Heading 6'),
            'UL LI': this.options._t('List'),
            'OL LI': this.options._t('List'),
            'CL LI': this.options._t('To-do'),
        };

        for (const hint of this.editable.querySelectorAll('.oe-hint')) {
            if (
                hint.classList.contains('oe-command-temporary-hint') ||
                !isEmptyBlock(hint) ||
                hint.querySelector('T[t-out]')
            ) {
                this.observerUnactive();
                hint.classList.remove('oe-hint', 'oe-command-temporary-hint');
                if (hint.classList.length === 0) {
                    hint.removeAttribute('class');
                }
                hint.removeAttribute('placeholder');
                this.observerActive();
            }
        }

        if (this.options.showEmptyElementHint) {
            for (const [selector, text] of Object.entries(selectors)) {
                for (const el of this.editable.querySelectorAll(selector)) {
                    if (!this.options.isHintBlacklisted(el)) {
                        this._makeHint(el, text);
                    }
                }
            }
        }

        const block = this.options.getPowerboxElement();
        if (block) {
            this._makeHint(block, this.options._t('Type "/" for commands'), true);
        }

        // placeholder hint
        const sel = this.document.getSelection();
        if (this.editable.textContent.trim() === '' && this.options.placeholder && this.editable.firstChild && this.editable.firstChild.innerHTML && !this.editable.contains(sel.focusNode)) {
            this._makeHint(this.editable.firstChild, this.options.placeholder, true);
        }
    }
    _makeHint(block, text, temporary = false) {
        const content = block && block.innerHTML.trim();
        if (
            block &&
            (content === '' || content === '<br>') &&
            !block.querySelector('T[t-out]') &&
            ancestors(block, this.editable).includes(this.editable)
        ) {
            this.observerUnactive();
            block.setAttribute('placeholder', text);
            block.classList.add('oe-hint');
            if (temporary) {
                block.classList.add('oe-command-temporary-hint');
            }
            this.observerActive();
        }
    }

    _fixSelectionOnContenteditableFalse() {
        const selection = this.document.getSelection();
        const { anchorNode, anchorOffset } = selection;
        const selectedPositionNode = anchorNode && anchorNode.nodeType === Node.ELEMENT_NODE &&
            anchorNode.childNodes[anchorOffset];
        if (anchorNode && closestElement(anchorNode, '[data-oe-protected="true"]')) {
            if (!(
                selectedPositionNode && selectedPositionNode.nodeType === Node.ELEMENT_NODE &&
                ['INPUT', 'TEXTAREA'].includes(selectedPositionNode.tagName)
            )) {
                selection.removeAllRanges();
            }
            return;
        }
        // When the browser set the selection inside a node that is
        // contenteditable=false, it breaks the edition upon keystroke. Move the
        // selection so that it remain in an editable area. An example of this
        // case happend when the selection goes into a fontawesome node.

        if (!selection.rangeCount) {
            return;
        }
        const range = selection.getRangeAt(0);
        const newRange = range.cloneRange();
        const startContainer = closestElement(range.startContainer);
        const endContainer = closestElement(range.endContainer);

        /**
         * Get last not editable node if the `node` is within `root` and is a
         * non editable node.
         *
         * Otherwise return `undefined`.
         *
         * Example:
         *
         * ```html
         * <div class="root" contenteditable="true">
         *     <div class="A">
         *         <div class="B" contenteditable="false">
         *             <div class="C">
         *             </div>
         *         </div>
         *     </div>
         * </div>
         * ```
         *
         * ```js
         * _getLastNotEditableAncestorOfNotEditable(document.querySelector(".C")) // return "B"
         * ```
         */
        function _getLastNotEditableAncestorOfNotEditable(node, root) {
            let currentNode = node;
            let lastEditable;
            if (!ancestors(node, root).includes(root)) {
                return;
            }
            while (currentNode && currentNode !== root) {
                if (currentNode.isContentEditable) {
                    return lastEditable;
                } else if (currentNode.isContentEditable === false) {
                    // By checking that the node is contentEditable === false,
                    // we ensure at the same time that the currentNode is a
                    // HTMLElement.
                    lastEditable = currentNode;
                }
                currentNode = currentNode.parentElement;
            }
            return lastEditable;
        }

        const startContainerNotEditable = _getLastNotEditableAncestorOfNotEditable(
            startContainer,
            this.editable,
        );
        const endContainerNotEditable = _getLastNotEditableAncestorOfNotEditable(
            endContainer,
            this.editable,
        );
        const bothNotEditable = startContainerNotEditable && endContainerNotEditable;

        if (startContainerNotEditable) {
            if (startContainerNotEditable.previousSibling) {
                newRange.setStart(
                    startContainerNotEditable.previousSibling,
                    startContainerNotEditable.previousSibling.length,
                );
                if (bothNotEditable) {
                    newRange.setEnd(
                        startContainerNotEditable.previousSibling,
                        startContainerNotEditable.previousSibling.length,
                    );
                }
            } else {
                newRange.setStart(startContainerNotEditable.parentElement, 0);
                if (bothNotEditable) {
                    newRange.setEnd(startContainerNotEditable.parentElement, 0);
                }
            }
        }
        if (!bothNotEditable && endContainerNotEditable) {
            if (endContainerNotEditable.nextSibling) {
                newRange.setEnd(endContainerNotEditable.nextSibling, 0);
            } else {
                newRange.setEnd(...endPos(endContainerNotEditable.parentElement));
            }
        }
        if (startContainerNotEditable || endContainerNotEditable) {
            selection.removeAllRanges();
            selection.addRange(newRange);
        }
    }

    /**
     * Places the cursor in a safe place (not the editable root).
     * Inserts an empty paragraph if selection results from mouse click and
     * there's no other way to insert text before/after a block.
     *
     * @param {Selection} selection - Collapsed selection at the editable root.
     * @param {String} currentKeyPress
     */
    _fixSelectionOnEditableRoot(selection, currentKeyPress) {
        let nodeAfterCursor = this.editable.childNodes[selection.anchorOffset];
        let nodeBeforeCursor = nodeAfterCursor && nodeAfterCursor.previousElementSibling;
        // Handle arrow key presses.
        if (currentKeyPress === 'ArrowRight' || currentKeyPress === 'ArrowDown') {
            while (nodeAfterCursor && isNotAllowedContent(nodeAfterCursor)) {
                nodeAfterCursor = nodeAfterCursor.nextElementSibling;
            }
            if (nodeAfterCursor) {
                setSelection(...getDeepestPosition(nodeAfterCursor, 0));
            } else {
                this.historyResetLatestComputedSelection(true);
            }
        } else if (currentKeyPress === 'ArrowLeft' || currentKeyPress === 'ArrowUp') {
            while (nodeBeforeCursor && isNotAllowedContent(nodeBeforeCursor)) {
                nodeBeforeCursor = nodeBeforeCursor.previousElementSibling;
            }
            if (nodeBeforeCursor) {
                setSelection(...getDeepestPosition(nodeBeforeCursor, nodeSize(nodeBeforeCursor)));
            } else {
                this.historyResetLatestComputedSelection(true);
            }
        // Handle cursor next to a 'P'.
        } else if (nodeAfterCursor && paragraphRelatedElements.includes(nodeAfterCursor.nodeName)) {
            // Cursor is right before a 'P'.
            setCursorStart(nodeAfterCursor);
        } else if (nodeBeforeCursor && paragraphRelatedElements.includes(nodeBeforeCursor.nodeName)) {
            // Cursor is right after a 'P'.
            setCursorEnd(nodeBeforeCursor);
        // Handle cursor not next to a 'P'.
        // Insert a new 'P' if selection resulted from a mouse click.
        } else if (this._currentMouseState === 'mousedown') {
            this._recordHistorySelection(true);
            const p = this.document.createElement('p');
            p.append(this.document.createElement('br'));
            if (!nodeAfterCursor) {
                // Cursor is at the end of the editable.
                this.editable.append(p);
            } else if (!nodeBeforeCursor) {
                // Cursor is at the beginning of the editable.
                this.editable.prepend(p);
            } else {
                // Cursor is between two non-p blocks
                nodeAfterCursor.before(p);
            }
            setCursorStart(p);
            this.historyStep();
        } else {
            // Remove selection as a fallback.
            selection.removeAllRanges();
        }
    }

    _onMouseup(ev) {
        this._currentMouseState = ev.type;

        this._fixFontAwesomeSelection();

        this._fixSelectionOnContenteditableFalse();
    }

    _onMouseDown(ev) {
        this._currentMouseState = ev.type;
        this._lastMouseClickPosition = [ev.x, ev.y];

        // When selecting all the text within a link then triggering delete or
        // inserting a character, the cursor and insertion is outside the link.
        // To avoid this problem, we make all editable zone become uneditable
        // except the link. Then when cliking outside the link, reset the
        // editable zones.
        const link = closestElement(ev.target, 'a');
        this.resetContenteditableLink();
        this._activateContenteditable();
        if (
            link && link.isContentEditable &&
            !link.querySelector('div') &&
            !closestElement(ev.target, '.o_not_editable')
        ) {
            this.setContenteditableLink(link);
        }
        // Ignore any changes that might have happened before this point.
        this.observer.takeRecords();

        const node = ev.target;
        // handle checkbox lists
        if (node.tagName == 'LI' && getListMode(node.parentElement) == 'CL') {
            const beforStyle = window.getComputedStyle(node, ':before');
            const style1 = {
                left: parseInt(beforStyle.getPropertyValue('left'), 10),
                top: parseInt(beforStyle.getPropertyValue('top'), 10),
            }
            style1.right = style1.left + parseInt(beforStyle.getPropertyValue('width'), 10);
            style1.bottom = style1.top + parseInt(beforStyle.getPropertyValue('height'), 10);

            const isMouseInsideCheckboxBox =
                ev.offsetX >= style1.left &&
                ev.offsetX <= style1.right &&
                ev.offsetY >= style1.top &&
                ev.offsetY <= style1.bottom;

            if (isMouseInsideCheckboxBox) {
                toggleClass(node, 'o_checked');
                ev.preventDefault();
                this.historyStep();
            }
        }

        // handle stars
        const isStar = el => el.nodeType === Node.ELEMENT_NODE && (
            el.classList.contains('fa-star') || el.classList.contains('fa-star-o')
        );
        if (isStar(node) &&
            node.parentElement && node.parentElement.className.includes('o_stars')) {
            const previousStars = getAdjacentPreviousSiblings(node, isStar);
            const nextStars = getAdjacentNextSiblings(node, isStar);
            if (nextStars.length || previousStars.length) {
                const shouldToggleOff = node.classList.contains('fa-star') &&
                    (!nextStars[0] || !nextStars[0].classList.contains('fa-star'));
                for (const star of [...previousStars, node]) {
                    star.classList.toggle('fa-star-o', shouldToggleOff);
                    star.classList.toggle('fa-star', !shouldToggleOff);
                };
                for (const star of nextStars) {
                    star.classList.toggle('fa-star-o', true);
                    star.classList.toggle('fa-star', false);
                };
                this.historyStep();
            }
        }

        // Handle table selection.
        if (this.toolbar && !ancestors(ev.target, this.editable).includes(this.toolbar)) {
            this.toolbar.style.pointerEvents = 'none';
            if (this.deselectTable() && hasValidSelection(this.editable)) {
                this.document.getSelection().collapseToStart();
            }
        }
        // Handle table resizing.
        const isHoveringTdBorder = this._isHoveringTdBorder(ev);
        if (isHoveringTdBorder) {
            ev.preventDefault();
            const direction = { top: 'row', right: 'col', bottom: 'row', left: 'col' }[isHoveringTdBorder] || false;
            let target1, target2;
            const column = closestElement(ev.target, 'tr');
            if (isHoveringTdBorder === 'top' && column) {
                target1 = getAdjacentPreviousSiblings(column).find(node => node.nodeName === 'TR');
                target2 = closestElement(ev.target, 'tr');
            } else if (isHoveringTdBorder === 'right') {
                target1 = ev.target;
                target2 = getAdjacentNextSiblings(ev.target).find(node => node.nodeName === 'TD');
            } else if (isHoveringTdBorder === 'bottom' && column) {
                target1 = closestElement(ev.target, 'tr');
                target2 = getAdjacentNextSiblings(column).find(node => node.nodeName === 'TR');
            } else if (isHoveringTdBorder === 'left') {
                target1 = getAdjacentPreviousSiblings(ev.target).find(node => node.nodeName === 'TD');
                target2 = ev.target;
            }
            this._isResizingTable = true;
            this._toggleTableResizeCursor(direction);
            const resizeTable = ev => this._resizeTable(ev, direction, target1, target2);
            const stopResizing = ev => {
                ev.preventDefault();
                this._isResizingTable = false;
                this._toggleTableResizeCursor(false);
                this.document.removeEventListener('mousemove', resizeTable);
                this.document.removeEventListener('mouseup', stopResizing);
                this.document.removeEventListener('mouseleave', stopResizing);
            };
            this.document.addEventListener('mousemove', resizeTable);
            this.document.addEventListener('mouseup', stopResizing);
            this.document.addEventListener('mouseleave', stopResizing);
        }
    }

    _onDocumentKeydown(ev) {
        const canUndoRedo = !['INPUT', 'TEXTAREA'].includes(this.document.activeElement.tagName);

        if (this.options.controlHistoryFromDocument && canUndoRedo) {
            if (IS_KEYBOARD_EVENT_UNDO(ev) && canUndoRedo) {
                ev.preventDefault();
                this.historyUndo();
            } else if (IS_KEYBOARD_EVENT_REDO(ev) && canUndoRedo) {
                ev.preventDefault();
                this.historyRedo();
            }
        } else {
            if (IS_KEYBOARD_EVENT_REDO(ev) || IS_KEYBOARD_EVENT_UNDO(ev)) {
                this._onKeyupResetContenteditableNodes.push(
                    ...this.editable.querySelectorAll('[contenteditable=true]'),
                );
                if (this.editable.getAttribute('contenteditable') === 'true') {
                    this._onKeyupResetContenteditableNodes.push(this.editable);
                }

                for (const node of this._onKeyupResetContenteditableNodes) {
                    this.automaticStepSkipStack();
                    node.setAttribute('contenteditable', false);
                }
            }
        }
    }

    _onDocumentKeyup() {
        if (this._onKeyupResetContenteditableNodes.length) {
            for (const node of this._onKeyupResetContenteditableNodes) {
                this.automaticStepSkipStack();
                node.setAttribute('contenteditable', true);
            }
            this._onKeyupResetContenteditableNodes = [];
        }
        this._fixSelectionOnContenteditableFalse();
    }

    _onDocumentMouseup() {
        if (this.toolbar) {
            this.toolbar.style.pointerEvents = 'auto';
        }
    }

    _onMousemove(ev) {
        if (this._currentMouseState === 'mousedown' && !this._isResizingTable) {
            this._handleSelectionInTable(ev);
        }
        if (!this._rowUi.classList.contains('o_open') && !this._columnUi.classList.contains('o_open')) {
            const column = closestElement(ev.target, 'td');
            if (this._isResizingTable || !column || !column.isContentEditable || !ev.target || ev.target.nodeType !== Node.ELEMENT_NODE) {
                this._toggleTableUi(false, false);
            } else {
                const row = closestElement(column, 'tr');
                const isFirstColumn = column === row.querySelector('td');
                const table = column && closestElement(column, 'table');
                const isFirstRow = table && row === table.querySelector('tr');
                this._toggleTableUi(isFirstColumn && row, isFirstRow && column);
            }
        }
        const direction = {top: 'row', right: 'col', bottom: 'row', left: 'col'}[this._isHoveringTdBorder(ev)] || false;
        if (direction || !this._isResizingTable) {
            this._toggleTableResizeCursor(direction);
        }
    }

    _onDocumentClick(ev) {
        // Close Table UI.
        this._rowUi.classList.remove('o_open');
        this._columnUi.classList.remove('o_open');
    }

    /**
     * @param {String} label
     * @param {String} url
     */
    _createLink(label, url) {
        const link = this.document.createElement('a');
        link.setAttribute('href', url);
        for (const [param, value] of Object.entries(this.options.defaultLinkAttributes)) {
            link.setAttribute(param, `${value}`);
        }
        link.innerText = label;
        return link;
    }
    /**
     * Add images inside the editable at the current selection.
     *
     * @param {File[]} imageFiles
     */
    addImagesFiles(imageFiles) {
        const promises = [];
        for (const imageFile of imageFiles) {
            const imageNode = document.createElement('img');
            imageNode.style.width = '100%';
            imageNode.classList.add('img-fluid');
            imageNode.dataset.fileName = imageFile.name;
            promises.push(getImageUrl(imageFile).then(url => {
                imageNode.src = url;
                return imageNode.outerHTML;
            }));
        }
        return Promise.all(promises).then(html => html.join(''));
    }
    /**
     * Handle safe pasting of html or plain text into the editor.
     */
    _onPaste(ev) {
        ev.preventDefault();
        const sel = this.document.getSelection();
        const files = getImageFiles(ev.clipboardData);
        const odooEditorHtml = ev.clipboardData.getData('text/odoo-editor');
        const clipboardHtml = ev.clipboardData.getData('text/html');
        const targetSupportsHtmlContent = isHtmlContentSupported(sel.anchorNode);
        // Replace entire link if its label is fully selected.
        const link = closestElement(sel.anchorNode, 'a');
        if (link && sel.toString().replace(/\u200B/g, '') === link.innerText.replace(/\u200B/g, '')) {
            const start = leftPos(link);
            // Exit link isolation since we're removing the link and editing outside of it.
            if (this._fixLinkMutatedElements && this._fixLinkMutatedElements.link === link) {
                this.resetContenteditableLink();
                this._activateContenteditable();
            }
            link.remove();
            setSelection(...start, ...start, false);
        }
        if (odooEditorHtml && targetSupportsHtmlContent) {
            const fragment = parseHTML(odooEditorHtml);
            DOMPurify.sanitize(fragment, { IN_PLACE: true });
            if (fragment.hasChildNodes()) {
                this._applyCommand('insert', fragment);
            }
        } else if ((files.length || clipboardHtml) && targetSupportsHtmlContent) {
            const clipboardElem = this._prepareClipboardData(clipboardHtml);
            // When copy pasting a table from the outside, a picture of the
            // table can be included in the clipboard as an image file. In that
            // particular case the html table is given a higher priority than
            // the clipboard picture.
            if (files.length && !clipboardElem.querySelector('table')) {
                this.addImagesFiles(files).then(html => this._applyCommand('insert', this._prepareClipboardData(html)));
            } else {
                this._applyCommand('insert', clipboardElem);
            }
        } else {
            const text = ev.clipboardData.getData('text/plain');
            const selectionIsInsideALink = !!closestElement(sel.anchorNode, 'a');
            let splitAroundUrl = [text];
            // Avoid transforming dynamic placeholder pattern to url.
            if(!text.match(/\${.*}/gi)) {
                splitAroundUrl = text.split(URL_REGEX);
            }
            if (splitAroundUrl.length === 3 && !splitAroundUrl[0] && !splitAroundUrl[2]) {
                // Pasted content is a single URL.
                const url = /^https?:\/\//i.test(text) ? text : 'https://' + text;
                const youtubeUrl = this.options.allowCommandVideo &&YOUTUBE_URL_GET_VIDEO_ID.exec(url);
                const urlFileExtention = url.split('.').pop();
                const isImageUrl = ['jpg', 'jpeg', 'png', 'gif', 'svg'].includes(urlFileExtention.toLowerCase());
                // A url cannot be transformed inside an existing link.
                // An image can be embedded inside an existing link, a video cannot.
                if (selectionIsInsideALink) {
                    if (isImageUrl) {
                        const img = document.createElement('IMG');
                        img.setAttribute('src', url);
                        this._applyCommand('insert', img);
                    } else {
                        this._applyCommand('insert', text);
                    }
                } else if (isImageUrl || youtubeUrl) {
                    // Open powerbox with commands to embed media or paste as link.
                    // Store history step index to revert it later.
                    const stepIndexBeforeInsert = this._historySteps.length - 1;
                    // Store mutations before text insertion, to reapply them after history revert.
                    this.observerFlush();
                    const currentStepMutations = [...this._currentStep.mutations];
                    // Insert URL as text, revert it later.
                    this._applyCommand('insert', text);
                    const revertTextInsertion = () => {
                        this.historyRevertUntil(stepIndexBeforeInsert);
                        this.historyStep(true);
                        this._historyStepsStates.set(peek(this._historySteps).id, 'consumed');
                        // Reapply mutations that were done before the text insertion.
                        this.historyApply(currentStepMutations);
                    };
                    let commands;
                    const pasteAsURLCommand = {
                        name: this.options._t('Paste as URL'),
                        description: this.options._t('Create an URL.'),
                        fontawesome: 'fa-link',
                        callback: () => {
                            revertTextInsertion();
                            this._applyRawCommand('insert', this._createLink(text, url))
                        },
                    };
                    if (isImageUrl) {
                        const embedImageCommand = {
                            name: this.options._t('Embed Image'),
                            description: this.options._t('Embed the image in the document.'),
                            fontawesome: 'fa-image',
                            callback: () => {
                                revertTextInsertion();
                                const img = document.createElement('IMG');
                                img.setAttribute('src', url);
                                this._applyRawCommand('insert', img);
                            },
                        };
                        commands = [embedImageCommand, pasteAsURLCommand];
                    } else {
                         // URL is a YouTube video.
                        const embedVideoCommand = {
                            name: this.options._t('Embed Youtube Video'),
                            description: this.options._t('Embed the youtube video in the document.'),
                            fontawesome: 'fa-youtube-play',
                            callback: () => {
                                revertTextInsertion();
                                let videoElement;
                                if (this.options.getYoutubeVideoElement) {
                                    videoElement = this.options.getYoutubeVideoElement(youtubeUrl[0]);
                                } else {
                                    videoElement = document.createElement('iframe');
                                    videoElement.setAttribute('width', '560');
                                    videoElement.setAttribute('height', '315');
                                    videoElement.setAttribute(
                                        'src',
                                        `https://www.youtube.com/embed/${encodeURIComponent(youtubeUrl[1])}`,
                                    );
                                    videoElement.setAttribute('title', 'YouTube video player');
                                    videoElement.setAttribute('frameborder', '0');
                                    videoElement.setAttribute(
                                        'allow',
                                        'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture',
                                    );
                                    videoElement.setAttribute('allowfullscreen', '1');
                                }
                                this._applyRawCommand('insert', videoElement);
                            },
                        };
                        commands = [embedVideoCommand, pasteAsURLCommand];
                    }
                    this.powerbox.open(commands);
                } else {
                    this._applyCommand('insert', this._createLink(text, url));
                }
            } else {
                this.historyPauseSteps();
                for (let i = 0; i < splitAroundUrl.length; i++) {
                    const url = /^https?:\/\//gi.test(splitAroundUrl[i])
                        ? splitAroundUrl[i]
                        : 'https://' + splitAroundUrl[i];
                    // Even indexes will always be plain text, and odd indexes will always be URL.
                    // only allow images emebed inside an existing link. No other url or video embed.
                    if (i % 2 && !selectionIsInsideALink) {
                        this._applyCommand('insert', this._createLink(splitAroundUrl[i], url));
                    } else if (splitAroundUrl[i] !== '') {
                        const textFragments = splitAroundUrl[i].split(/\r?\n/);
                        let textIndex = 1;
                        for (const textFragment of textFragments) {
                            this._applyCommand('insert', textFragment);
                            if (textIndex < textFragments.length) {
                                this._applyCommand('oShiftEnter');
                            }
                            textIndex++;
                        }
                    }
                }
                this.historyUnpauseSteps();
                this.historyStep();
            }
        }
    }
    _onDragStart(ev) {
        if (ev.target.nodeName === 'IMG') {
            ev.dataTransfer.setData('text/plain', `oid:${ev.target.oid}`);
        }
    }
    /**
     * Handle safe dropping of html into the editor.
     */
    _onDrop(ev) {
        ev.preventDefault();
        if (!isHtmlContentSupported(ev.target)) {
            return;
        }
        const sel = this.document.getSelection();
        let isInEditor = false;
        let ancestor = sel.anchorNode;
        while (ancestor && !isInEditor) {
            if (ancestor === this.editable) {
                isInEditor = true;
            }
            ancestor = ancestor.parentNode;
        }
        const dataTransfer = (ev.originalEvent || ev).dataTransfer;
        const imageOidMatch = (dataTransfer.getData('text') || '').match('oid:(.*)');
        const imageOid = imageOidMatch && imageOidMatch[1];
        const image = imageOid && [...this.editable.querySelectorAll('*')].find(
            node => node.oid === imageOid,
        );
        const fileTransferItems = getImageFiles(dataTransfer);
        const htmlTransferItem = [...dataTransfer.items].find(
            item => item.type === 'text/html',
        );
        if (image || fileTransferItems.length || htmlTransferItem) {
            if (this.document.caretPositionFromPoint) {
                const range = this.document.caretPositionFromPoint(ev.clientX, ev.clientY);
                setSelection(range.offsetNode, range.offset);
            } else if (this.document.caretRangeFromPoint) {
                const range = this.document.caretRangeFromPoint(ev.clientX, ev.clientY);
                setSelection(range.startContainer, range.startOffset);
            }
        }
        if (image) {
            image.classList.toggle('img-fluid', true);
            const html = image.outerHTML;
            image.remove();
            this.execCommand('insert', this._prepareClipboardData(html));
        } else if (fileTransferItems.length) {
            this.addImagesFiles(fileTransferItems).then(html => {
                this.execCommand('insert', this._prepareClipboardData(html));
            });
        } else if (htmlTransferItem) {
            htmlTransferItem.getAsString(pastedText => {
                this.execCommand('insert', this._prepareClipboardData(pastedText));
            });
        }
        this.historyStep();
    }

    _onTabulationInTable(ev) {
        const sel = this.document.getSelection();
        const closestTable = closestElement(sel.anchorNode, 'table');
        if (!closestTable) {
            return;
        }
        const closestTd = closestElement(sel.anchorNode, 'td');
        const tds = [...closestTable.querySelectorAll('td')];
        const direction = ev.shiftKey ? DIRECTIONS.LEFT : DIRECTIONS.RIGHT;
        const cursorDestination =
            tds[tds.findIndex(td => closestTd === td) + (direction === DIRECTIONS.LEFT ? -1 : 1)];
        if (cursorDestination) {
            setSelection(...startPos(cursorDestination), ...endPos(cursorDestination), true);
        } else if (direction === DIRECTIONS.RIGHT) {
            this.execCommand('addRow', 'after');
            this._onTabulationInTable(ev);
        }
    }
    _onTableMenuTogglerClick(ev) {
        const uiWrapper = closestElement(ev.target, '.o_table_ui');
        uiWrapper.classList.toggle('o_open');
        if (uiWrapper.classList.contains('o_column_ui')) {
            const columnIndex = getColumnIndex(this._columnUiTarget);
            uiWrapper.querySelector('.o_move_left').classList.toggle('o_hide', columnIndex === 0);
            const shouldHideRight = columnIndex === [...this._columnUiTarget.parentElement.children].filter(child => child.nodeName === 'TD').length - 1;
            uiWrapper.querySelector('.o_move_right').classList.toggle('o_hide', shouldHideRight);
        } else {
            const rowIndex = getRowIndex(this._rowUiTarget);
            uiWrapper.querySelector('.o_move_up').classList.toggle('o_hide', rowIndex === 0);
            const shouldHideDown = rowIndex === [...this._rowUiTarget.parentElement.children].filter(child => child.nodeName === 'TR').length - 1;
            uiWrapper.querySelector('.o_move_down').classList.toggle('o_hide', shouldHideDown);
        }
        ev.stopPropagation();
    }
    _onTableMoveUpClick() {
        if (this._rowUiTarget.previousSibling) {
            this._rowUiTarget.previousSibling.before(this._rowUiTarget);
        }
    }
    _onTableMoveDownClick() {
        if (this._rowUiTarget.nextSibling) {
            this._rowUiTarget.nextSibling.after(this._rowUiTarget);
        }
    }
    _onTableMoveRightClick() {
        const trs = [...this._columnUiTarget.parentElement.parentElement.children].filter(child => child.nodeName === 'TR');
        const columnIndex = getColumnIndex(this._columnUiTarget);
        const tdsToMove = trs.map(tr => [...tr.children].filter(child => child.nodeName === 'TD')[columnIndex]);
        for (const tdToMove of tdsToMove) {
            const target = [...tdToMove.parentElement.children].filter(child => child.nodeName === 'TD')[columnIndex + 1];
            target.after(tdToMove);
        }
    }
    _onTableMoveLeftClick() {
        const trs = [...this._columnUiTarget.parentElement.parentElement.children].filter(child => child.nodeName === 'TR');
        const columnIndex = getColumnIndex(this._columnUiTarget);
        const tdsToMove = trs.map(tr => [...tr.children].filter(child => child.nodeName === 'TD')[columnIndex]);
        for (const tdToMove of tdsToMove) {
            const target = [...tdToMove.parentElement.children].filter(child => child.nodeName === 'TD')[columnIndex - 1];
            target.before(tdToMove);
        }
    }
    _onTableDeleteColumnClick() {
        this.historyPauseSteps();
        const rows = [...closestElement(this._columnUiTarget, 'tr').parentElement.children].filter(child => child.nodeName === 'TR');
        this.execCommand('removeColumn', this._columnUiTarget);
        if (rows.every(row => !row.parentElement)) {
            this.execCommand('deleteTable', this.editable.querySelector('.o_selected_table'));
        }
        this.historyUnpauseSteps();
        this.historyStep();
    }
    _onTableDeleteRowClick() {
        this.historyPauseSteps();
        const rows = [...this._rowUiTarget.parentElement.children].filter(child => child.nodeName === 'TR');
        this.execCommand('removeRow', this._rowUiTarget);
        if (rows.every(row => !row.parentElement)) {
            this.execCommand('deleteTable', this.editable.querySelector('.o_selected_table'));
        }
        this.historyUnpauseSteps();
        this.historyStep();
    }

    /**
     * Fix the current selection range in case the range start or end inside a fontAwesome node
     */
    _fixFontAwesomeSelection() {
        const selection = this.document.getSelection();
        if (
            selection.isCollapsed ||
            (selection.anchorNode &&
                !ancestors(selection.anchorNode, this.editable).includes(this.editable))
        )
            return;
        let shouldUpdateSelection = false;
        const fixedSelection = {
            anchorNode: selection.anchorNode,
            anchorOffset: selection.anchorOffset,
            focusNode: selection.focusNode,
            focusOffset: selection.focusOffset,
        };
        const selectionDirection = getCursorDirection(
            selection.anchorNode,
            selection.anchorOffset,
            selection.focusNode,
            selection.focusOffset,
        );
        // check and fix anchor node
        const closestAnchorNodeEl = closestElement(selection.anchorNode);
        if (isFontAwesome(closestAnchorNodeEl)) {
            shouldUpdateSelection = true;
            fixedSelection.anchorNode =
                selectionDirection === DIRECTIONS.RIGHT
                    ? closestAnchorNodeEl.previousSibling
                    : closestAnchorNodeEl.nextSibling;
            if (fixedSelection.anchorNode) {
                fixedSelection.anchorOffset =
                    selectionDirection === DIRECTIONS.RIGHT ? fixedSelection.anchorNode.length : 0;
            } else {
                fixedSelection.anchorNode = closestAnchorNodeEl.parentElement;
                fixedSelection.anchorOffset = 0;
            }
        }
        // check and fix focus node
        const closestFocusNodeEl = closestElement(selection.focusNode);
        if (isFontAwesome(closestFocusNodeEl)) {
            shouldUpdateSelection = true;
            fixedSelection.focusNode =
                selectionDirection === DIRECTIONS.RIGHT
                    ? closestFocusNodeEl.nextSibling
                    : closestFocusNodeEl.previousSibling;
            if (fixedSelection.focusNode) {
                fixedSelection.focusOffset =
                    selectionDirection === DIRECTIONS.RIGHT ? 0 : fixedSelection.focusNode.length;
            } else {
                fixedSelection.focusNode = closestFocusNodeEl.parentElement;
                fixedSelection.focusOffset = 0;
            }
        }
        if (shouldUpdateSelection) {
            setSelection(
                fixedSelection.anchorNode,
                fixedSelection.anchorOffset,
                fixedSelection.focusNode,
                fixedSelection.focusOffset,
                false,
            );
        }
    }
    _pluginAdd(Plugin) {
        this._plugins.push(new Plugin({ editor: this }));
    }
    _pluginCall(method, args) {
        for (const plugin of this._plugins) {
            if (plugin[method]) {
                plugin[method](...args);
            }
        }
    }
}
