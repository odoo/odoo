/** @odoo-module **/

import { ancestors } from '@web_editor/js/common/wysiwyg_utils';
import { closestElement } from "@web_editor/js/editor/odoo-editor/src/utils/utils";

export class QWebPlugin {
    constructor(options = {}) {
        this._options = options;
        if (this._options.editor) {
            this._editable = this._options.editor.editable;
            this._document = this._options.editor.document;
            this._selectQwebNode(this._options.editor);
        } else {
            this._editable = this._options.editable;
            this._document = this._options.document || window.document;
        }
        this._getContextFromParentRect = this._options.editor?.options?.getContextFromParentRect || (() => ({ top: 0, left: 0 }));
        this._editable = this._options.editable || (this._options.editor && this._options.editor.editable);
        this._document = this._options.document || (this._options.editor && this._options.editor.document) || window.document;
        this._tGroupCount = 0;
        this._hideBranchingSelection = this._hideBranchingSelection.bind(this);
        this._makeBranchingSelection();
        this._clickListeners = [];
    }
    destroy() {
        this._selectElWrapper.remove();
        for (const listener of this._clickListeners) {
            document.removeEventListener('click', listener);
        }
    }
    cleanForSave(editable) {
        for (const node of editable.querySelectorAll('[data-oe-t-group], [data-oe-t-inline], [data-oe-t-selectable], [data-oe-t-group-active]')) {
            node.removeAttribute('data-oe-t-group-active');
            node.removeAttribute('data-oe-t-group');
            node.removeAttribute('data-oe-t-inline');
            node.removeAttribute('data-oe-t-selectable');
        }
    }
    sanitizeElement(subRoot) {
        if (subRoot.nodeType !== Node.ELEMENT_NODE) {
            return;
        }
        if (this._options.editor) {
            this._options.editor.observerUnactive('qweb-plugin-sanitize');
        }

        this._fixInlines(subRoot);

        const demoElements = subRoot.querySelectorAll('[t-esc], [t-raw], [t-out], [t-field]');
        for (const element of demoElements) {
            element.setAttribute('contenteditable', 'false');
        }

        this._groupQwebBranching(subRoot);
        if (this._options.editor) {
            this._options.editor.observerActive('qweb-plugin-sanitize');
        }
    }
    _groupQwebBranching(subRoot) {
        const tNodes = subRoot.querySelectorAll('[t-if], [t-elif], [t-else]');
        const groupsEncounter = new Set();
        for (const node of tNodes) {
            const parentTNode = [...node.parentElement.children];
            const index = parentTNode.indexOf(node);
            const prevNode = parentTNode[index - 1];

            let groupId;
            if (
                prevNode &&
                node.previousElementSibling === prevNode &&
                !node.hasAttribute('t-if')
            ) {
                // Make the first t-if selectable, if prevNode is not a t-if,
                // it's already data-oe-t-selectable.
                prevNode.setAttribute('data-oe-t-selectable', 'true');
                groupId = parseInt(prevNode.getAttribute('data-oe-t-group'));
                node.setAttribute('data-oe-t-selectable', 'true');
            } else {
                groupId = this._tGroupCount++;
            }
            groupsEncounter.add(groupId);
            node.setAttribute('data-oe-t-group', groupId);

            const clickListener = e => {
                e.stopImmediatePropagation();
                this._showBranchingSelection(node);
            };
            this._clickListeners.push(clickListener);
            node.addEventListener('click', clickListener);
        }
        for (const groupId of groupsEncounter) {
            const isOneElementActive = subRoot.querySelector(
                `[data-oe-t-group='${groupId}'][data-oe-t-group-active]`,
            );
            // If there is no element in groupId activated, activate the first
            // one.
            if (!isOneElementActive) {
                subRoot
                    .querySelector(`[data-oe-t-group='${groupId}']`)
                    .setAttribute('data-oe-t-group-active', 'true');
            }
        }
    }
    _fixInlines(subRoot) {
        const checkAllInline = el => {
            return [...el.children].every(child => {
                if (child.tagName === 'T') {
                    return checkAllInline(child);
                } else {
                    return (
                        child.nodeType !== Node.ELEMENT_NODE ||
                        window.getComputedStyle(child).display === 'inline'
                    );
                }
            });
        };
        const tElements = subRoot.querySelectorAll('t');
        // Wait for the content to be on the dom to check checkAllInline
        // otherwise the getComputedStyle will be wrong.
        // todo: remove the setTimeout when the editor will provide a signal
        // that the editable is on the dom.
        setTimeout(() => {
            if (this._options.editor) {
                this._options.editor.observerUnactive('qweb-plugin-checkAllInline');
            }
            for (const tElement of tElements) {
                if (checkAllInline(tElement)) {
                    tElement.setAttribute('data-oe-t-inline', 'true');
                }
            }
            if (this._options.editor) {
                this._options.editor.observerActive('qweb-plugin-checkAllInline');
            }
        });
    }
    _selectQwebNode(editor) {
        editor.addDomListener(editor.document, 'selectionchange', e => {
            const selection = editor.document.getSelection();
            const qwebNode = selection.anchorNode && closestElement(selection.anchorNode, '[t-field],[t-esc],[t-out]');
            if (qwebNode){
                const range = new Range();
                range.selectNode(qwebNode);
                selection.removeAllRanges();
                selection.addRange(range);
            }
        });
    }
    _makeBranchingSelection() {
        const document = this._options.document || window.document;
        this._selectElWrapper = document.createElement('div');
        this._selectElWrapper.classList.add('oe-qweb-select');
        this._selectElWrapper.innerHTML = '';
        document.body.append(this._selectElWrapper);
        this._hideBranchingSelection();
    }
    _showBranchingSelection(target) {
        this._hideBranchingSelection();

        const branchingHierarchyElements = [target, ...ancestors(target, this._editable)]
            .filter(element => element.getAttribute('data-oe-t-group-active') === 'true')
            .filter(element => {
                const itemGroupId = element.getAttribute('data-oe-t-group');

                const groupItemsNodes = element.parentElement.querySelectorAll(
                    `[data-oe-t-group='${itemGroupId}']`,
                );
                return groupItemsNodes.length > 1;
            });

        if (!branchingHierarchyElements.length) return;

        const groupsActive = branchingHierarchyElements.map(node =>
            node.getAttribute('data-oe-t-group'),
        );
        for (const branchingElement of branchingHierarchyElements) {
            this._selectElWrapper.prepend(this._renderBranchingSelection(branchingElement));
        }
        const closeSelectHandler = event => {
            const path = [event.target, ...ancestors(event.target)];
            const shouldClose = !path.find(
                element =>
                    element === this._selectElWrapper ||
                    groupsActive.includes(element.getAttribute('data-oe-t-group')),
            );
            if (shouldClose) {
                this._hideBranchingSelection();
                document.removeEventListener('mousedown', closeSelectHandler);
            }
        };
        document.addEventListener('mousedown', closeSelectHandler);
        this._selectElWrapper.style.display = 'flex';
        this._updateBranchingSelectionPosition(
            branchingHierarchyElements[branchingHierarchyElements.length - 1],
        );
    }
    _updateBranchingSelectionPosition(target) {
        window.addEventListener('mousewheel', this._hideBranchingSelection);

        const box = target.getBoundingClientRect();
        const selBox = this._selectElWrapper.getBoundingClientRect();
        const parentBox = this._getContextFromParentRect();

        const left = parentBox.left + window.scrollX + box.left;
        const top = parentBox.top + window.scrollY + box.top - selBox.height;

        this._selectElWrapper.style.left = `${left}px`;
        this._selectElWrapper.style.top = `${top}px`;
    }
    _renderBranchingSelection(target) {
        const selectEl = document.createElement('select');
        const groupId = parseInt(target.getAttribute('data-oe-t-group'));
        const groupElements = target.parentElement.querySelectorAll(
            `[data-oe-t-group='${groupId}']`,
        );
        for (const element of groupElements) {
            const optionElement = document.createElement('option');
            if (element.hasAttribute('t-if')) {
                optionElement.innerText = `if: "${element.getAttribute("t-if")}"`;
            } else if (element.hasAttribute('t-elif')) {
                optionElement.innerText = `elif: "${element.getAttribute("t-elif")}"`;
            } else if (element.hasAttribute('t-else')) {
                optionElement.innerText = 'else';
            }
            if (element.hasAttribute('data-oe-t-group-active')) {
                optionElement.selected = true;
            }
            selectEl.appendChild(optionElement);
        }

        selectEl.onchange = () => {
            let activeElement;
            for (let i = 0; i < groupElements.length; i++) {
                if (i === selectEl.selectedIndex) {
                    activeElement = groupElements[i];
                    groupElements[i].setAttribute('data-oe-t-group-active', 'true');
                } else {
                    groupElements[i].removeAttribute('data-oe-t-group-active');
                }
            }
            this._showBranchingSelection(activeElement);
        };
        return selectEl;
    }
    _hideBranchingSelection() {
        this._selectElWrapper.style.display = 'none';
        this._selectElWrapper.innerHTML = ``;
        window.removeEventListener('mousewheel', this._hideBranchingSelection);
    }
}
