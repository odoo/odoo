/** @odoo-module */

import { Component, onMounted, onPatched, useExternalListener, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { fuzzyLookup } from "@web/core/utils/search";
import { rotate } from "@web/core/utils/arrays";

const categories = registry.category("powerbox_categories");
const commands = registry.category("powerbox_commands");

export class Powerbox extends Component {
    static template = "html_editor.Powerbox";
    static props = {
        onMounted: Function,
        close: Function,
        dispatch: Function,
        el: HTMLElement,
    };

    setup() {
        const ref = useRef("root");
        this.search = "";
        this.cmdIndex = 0;
        // text node and offset for the / character
        this.node = null;
        this.offset = 0;
        this.endOffset = 0;
        this.commands = null;
        this.categories = null;
        this.computeCommands();

        onMounted(() => {
            this.props.onMounted(ref.el);
            const range = window.getSelection().getRangeAt(0);
            this.node = range.startContainer;
            if (!range.collapsed || this.node instanceof Element) {
                throw new Error("Need to check if this is legit...");
            }
            this.offset = range.startOffset - 1;
            this.endOffset = this.offset + 1;
            const prevChar = this.node.nodeValue[this.offset];
            if (prevChar !== "/") {
                this.props.close();
            }
        });
        onPatched(() => {
            const activeCommand = ref.el.querySelector(".o-we-command.active");
            if (activeCommand) {
                activeCommand.scrollIntoView({ block: "nearest", inline: "nearest" });
            }
        });

        useExternalListener(this.props.el, "keydown", (ev) => {
            const key = ev.key;
            switch (key) {
                case "Escape":
                    this.props.close();
                    break;
                case "Enter":
                    ev.preventDefault();
                    this.applyCurrentCommand();
                    break;
                case "ArrowUp":
                    ev.preventDefault();
                    this.cmdIndex = rotate(this.cmdIndex, this.commands, -1);
                    this.render();
                    break;
                case "ArrowDown":
                    ev.preventDefault();
                    this.cmdIndex = rotate(this.cmdIndex, this.commands, 1);
                    this.render();
                    break;
            }
        });

        useExternalListener(this.props.el, "input", (ev) => {
            const range = window.getSelection().getRangeAt(0);
            if (!this.isSearching(range)) {
                this.props.close();
                return;
            }
            this.endOffset = range.endOffset;
            const search = this.node.nodeValue.slice(this.offset + 1, this.endOffset);
            this.computeCommands(search);
            this.render();
        });
        useExternalListener(document, "mousedown", (ev) => {
            this.props.close();
        });
    }

    isSearching(range) {
        return (
            range.endContainer === this.node &&
            this.node.nodeValue[this.offset] === "/" &&
            range.endOffset >= this.offset
        );
    }

    computeCommands(search = "") {
        this.commands = [];
        this.categories = [];
        for (const [id, category] of categories.getEntries()) {
            let cmds = commands.getAll().filter((cmd) => cmd.category === id);
            if (search) {
                cmds = fuzzyLookup(search.toLowerCase(), cmds, (cmd) =>
                    (cmd.name + cmd.description + category.name).toLowerCase()
                );
            }
            this.commands.push(...cmds);
            if (cmds.length) {
                this.categories.push({
                    name: category.name,
                    commands: cmds,
                });
            }
        }
        this.cmdIndex = 0;
        if (!this.commands.length) {
            this.props.close();
        }
    }

    activateCommand(command) {
        const index = this.commands.indexOf(command);
        if (index > -1) {
            this.cmdIndex = index;
            this.render();
        }
    }

    applyCommand(command) {
        const selection = window.getSelection();
        const nodeValue = this.node.nodeValue;
        const newValue = nodeValue.slice(0, this.offset) + nodeValue.slice(this.endOffset);
        this.node.nodeValue = newValue;
        selection.setPosition(this.node, this.offset);
        command.action(this.props.dispatch);
        this.props.close();
    }

    applyCurrentCommand() {
        this.applyCommand(this.commands[this.cmdIndex]);
    }
}
