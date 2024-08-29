import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { QWebPicker } from "./qweb_picker";

const isUnsplittableQWebElement = (element) =>
    element.tagName === "T" ||
    ["t-field", "t-if", "t-elif", "t-else", "t-foreach", "t-value", "t-esc", "t-out", "t-raw"].some(
        (attr) => element.getAttribute(attr)
    );

export class QWebPlugin extends Plugin {
    static name = "qweb";
    static dependencies = ["overlay", "selection"];
    /** @type { (p: QWebPlugin) => Record<string, any> } */
    static resources = (p) => ({
        onSelectionChange: p.onSelectionChange.bind(p),
        is_mutation_record_savable: p.isMutationRecordSavable.bind(p),
        isUnremovable: (element) => element.getAttribute("t-set") || element.getAttribute("t-call"),
        isUnsplittable: isUnsplittableQWebElement,
    });

    setup() {
        this.editable.classList.add("odoo-editor-qweb");
        this.picker = this.shared.createOverlay(QWebPicker, { position: "top-start" });
        this.addDomListener(this.editable, "click", this.onClick);
        this.groupIndex = 0;
    }
    isMutationRecordSavable(mutationRecord) {
        if (mutationRecord.type === "attributes") {
            if (
                [
                    "data-oe-t-group",
                    "data-oe-t-inline",
                    "data-oe-t-selectable",
                    "data-oe-t-group-active",
                ].includes(mutationRecord.attributeName)
            ) {
                return false;
            }
        }
        return true;
    }

    handleCommand(command, payload) {
        switch (command) {
            case "NORMALIZE":
                this.normalize(payload.node);
                break;
            case "CLEAN":
                this.clearDataAttributes(payload.root);
                break;
            case "CLEAN_FOR_SAVE":
                this.clearDataAttributes(payload.root);
                for (const element of payload.root.querySelectorAll(
                    "[t-esc], [t-raw], [t-out], [t-field]"
                )) {
                    element.removeAttribute("contenteditable");
                }
                break;
        }
    }

    onSelectionChange(selection) {
        const documentSelection = this.document.getSelection();
        const qwebNode =
            documentSelection &&
            documentSelection.anchorNode &&
            closestElement(documentSelection.anchorNode, "[t-field],[t-esc],[t-out]");
        if (qwebNode && this.editable.contains(qwebNode)) {
            // select the whole qweb node
            this.shared.setSelection(selection);
        }
    }

    normalize(root) {
        this.normalizeInline(root);

        for (const element of root.querySelectorAll("[t-esc], [t-raw], [t-out], [t-field]")) {
            element.setAttribute("contenteditable", "false");
        }
        this.applyGroupQwebBranching(root);
    }

    checkAllInline(el) {
        return [...el.children].every((child) => {
            if (child.tagName === "T") {
                return this.checkAllInline(child);
            } else {
                return (
                    child.nodeType !== Node.ELEMENT_NODE ||
                    this.document.defaultView.getComputedStyle(child).display === "inline"
                );
            }
        });
    }

    normalizeInline(root) {
        for (const el of root.querySelectorAll("t")) {
            if (this.checkAllInline(el)) {
                el.setAttribute("data-oe-t-inline", "true");
            }
        }
    }

    getNodeGroups(node) {
        const branchNode = node.closest("[data-oe-t-group]");
        if (!branchNode) {
            return [];
        }
        const groupId = branchNode.getAttribute("data-oe-t-group");
        const group = [];
        for (const node of branchNode.parentElement.querySelectorAll(
            `[data-oe-t-group='${groupId}']`
        )) {
            let label = "";
            if (node.hasAttribute("t-if")) {
                label = `if: ${node.getAttribute("t-if")}`;
            } else if (node.hasAttribute("t-elif")) {
                label = `elif: ${node.getAttribute("t-elif")}`;
            } else if (node.hasAttribute("t-else")) {
                label = "else";
            }
            group.push({
                groupId,
                node,
                label,
                isActive: node.getAttribute("data-oe-t-group-active") === "true",
            });
        }
        return this.getNodeGroups(branchNode.parentElement).concat([group]);
    }

    onClick(ev) {
        this.picker.close();
        const targetNode = ev.target;
        if (targetNode.closest("[data-oe-t-group]")) {
            this.selectNode(targetNode);
        }
    }

    selectNode(node) {
        this.selectedNode = node;
        this.picker.open({
            target: node,
            props: {
                groups: this.getNodeGroups(node),
                select: this.select.bind(this),
            },
        });
    }

    applyGroupQwebBranching(root) {
        const tNodes = root.querySelectorAll("[t-if], [t-elif], [t-else]");
        const groupsEncounter = new Set();
        for (const node of tNodes) {
            const prevNode = node.previousElementSibling;

            let groupId;
            if (prevNode && !node.hasAttribute("t-if")) {
                // Make the first t-if selectable, if prevNode is not a t-if,
                // it's already data-oe-t-selectable.
                prevNode.setAttribute("data-oe-t-selectable", "true");
                groupId = parseInt(prevNode.getAttribute("data-oe-t-group"));
                node.setAttribute("data-oe-t-selectable", "true");
            } else {
                groupId = this.groupIndex++;
            }
            groupsEncounter.add(groupId);
            node.setAttribute("data-oe-t-group", groupId);
        }
        for (const groupId of groupsEncounter) {
            const isOneElementActive = root.querySelector(
                `[data-oe-t-group='${groupId}'][data-oe-t-group-active]`
            );
            // If there is no element in groupId activated, activate the first
            // one.
            if (!isOneElementActive) {
                root.querySelector(`[data-oe-t-group='${groupId}']`).setAttribute(
                    "data-oe-t-group-active",
                    "true"
                );
            }
        }
    }

    select(node) {
        const groupId = node.getAttribute("data-oe-t-group");
        const activeElement = node.parentElement.querySelector(
            `[data-oe-t-group='${groupId}'][data-oe-t-group-active]`
        );
        if (activeElement === node) {
            return;
        }
        activeElement.removeAttribute("data-oe-t-group-active");
        node.setAttribute("data-oe-t-group-active", "true");
        this.selectedNode = node;
        this.picker.close();
        this.selectNode(node);
    }

    clearDataAttributes(root) {
        for (const node of root.querySelectorAll(
            "[data-oe-t-group], [data-oe-t-inline], [data-oe-t-selectable], [data-oe-t-group-active]"
        )) {
            node.removeAttribute("data-oe-t-group-active");
            node.removeAttribute("data-oe-t-group");
            node.removeAttribute("data-oe-t-inline");
            node.removeAttribute("data-oe-t-selectable");
        }
    }
}
