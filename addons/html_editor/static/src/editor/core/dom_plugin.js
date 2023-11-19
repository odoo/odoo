/** @odoo-module */

import { Plugin } from "../plugin";

export class DomPlugin extends Plugin {
    static name = "dom";

    handleCommand(command, payload) {
        switch (command) {
            case "TOGGLE_BOLD":
                this.toggleTag("strong");
                break;
            case "TOGGLE_ITALIC":
                this.toggleTag("em");
                break;
            case "TOGGLE_UNDERLINE":
                this.toggleTag("u");
                break;
            case "TOGGLE_STRIKETHROUGH":
                this.toggleTag("s");
                break;
            case "SET_TAG":
                this.setTag(payload);
                break;
            case "INSERT_SEPARATOR":
                this.insertSeparator();
                break;
            case "TOGGLE_LIST":
                this.toggleList(payload.type);
                break;
            case "TOGGLE_CHECKLIST":
                this.toggleChecklist();
                break;
        }
    }

    // --------------------------------------------------------------------------
    // commands
    // --------------------------------------------------------------------------

    toggleTag(tagName) {
        const selection = document.getSelection();
        const range = selection.getRangeAt(0);
        const fragment = range.extractContents();
        const elem = document.createElement(tagName);
        elem.appendChild(fragment);
        range.insertNode(elem);
        selection.selectAllChildren(elem);
    }

    setTag({ tagName }) {
        const selection = document.getSelection();
        const range = selection.getRangeAt(0);
        const node = range.endContainer;
        const offset = range.endOffset;
        const elem = range.endContainer.parentElement;
        const newElem = document.createElement(tagName);
        const children = [...elem.childNodes];
        let hasOnlyEmptyTextNodes = true;
        for (const child of children) {
            newElem.appendChild(child);
            if (!(child instanceof Text) || child.nodeValue !== "") {
                hasOnlyEmptyTextNodes = false;
            }
        }
        if (hasOnlyEmptyTextNodes) {
            newElem.appendChild(document.createElement("BR"));
        }
        elem.replaceWith(newElem);
        selection.setPosition(node, offset);
    }

    insertSeparator() {
        const selection = document.getSelection();
        const range = selection.getRangeAt(0);
        const sep = document.createElement("hr");
        const target = range.commonAncestorContainer;
        target.parentElement.before(sep);
    }

    toggleList(type) {
        if (type !== "UL" && type !== "OL") {
            throw new Error(`Invalid list type: ${type}`);
        }
        const selection = document.getSelection();
        const range = selection.getRangeAt(0);
        const currentNode = range.endContainer;
        const offset = range.endOffset;
        const elem = currentNode.parentElement;
        const list = document.createElement(type);
        const li = document.createElement("li");
        list.appendChild(li);
        li.appendChild(currentNode);
        elem.replaceWith(list);
        selection.setPosition(currentNode, offset);
        return list;
    }

    toggleChecklist() {
        const list = this.toggleList("UL");
        list.classList.add("o_checklist");
    }
}
