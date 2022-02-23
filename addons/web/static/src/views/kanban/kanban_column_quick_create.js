/** @odoo-module */
import { Dialog } from "@web/core/dialog/dialog";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _lt } from "@web/core/l10n/translation";
import { useAutofocus, useService } from "@web/core/utils/hooks";

const { Component, useExternalListener, useState, useRef } = owl;

export class KanbanColumnQuickCreate extends Component {
    setup() {
        this.dialog = useService("dialog");
        this.root = useRef("root");
        this.state = useState({
            columnTitle: "",
        });

        useAutofocus();

        // Close on outside click
        useExternalListener(window, "mousedown", (/** @type {MouseEvent} */ ev) => {
            // This target is kept in order to impeach close on outside click behavior if the click
            // has been initiated from the quickcreate root element (mouse selection in an input...)
            this.mousedownTarget = ev.target;
        });
        useExternalListener(window, "click", (/** @type {MouseEvent} */ ev) => {
            const target = this.mousedownTarget || ev.target;
            const gotClickedInside = this.root.el.contains(target);
            if (!gotClickedInside) {
                this.fold();
            }
            this.mousedownTarget = null;
        });

        // Key Navigation
        // FIXME ? Maybe it will also validate even if enter is pressed outside of the quick create machin
        useHotkey("enter", () => this.validate());
        useHotkey("escape", () => this.fold());
    }

    fold() {
        this.props.onFoldChange(true);
    }

    unfold() {
        this.props.onFoldChange(false);
    }

    validate() {
        if (this.state.columnTitle.length) {
            this.props.onValidate(this.state.columnTitle);
        }
    }

    showExamples() {
        this.dialog.add(KanbanColumnExamplesDialog, {
            examples: this.props.exampleData.examples,
            applyExamplesText:
                this.props.exampleData.applyExamplesText || this.env._t("Use This For My Kanban"),
            applyExamples: (index) => {
                for (const groupName of this.props.exampleData.examples[index].columns) {
                    this.props.onValidate(groupName);
                }
            },
        });
    }
}
KanbanColumnQuickCreate.template = "web.KanbanColumnQuickCreate";

class KanbanColumnExamplesDialog extends Dialog {
    setup() {
        super.setup(...arguments);
        this.navList = useRef("navList");
    }

    random(min, max) {
        return new Array(Math.floor(Math.random() * (max - min) + min));
    }

    applyExamples() {
        const ul = this.navList.el;
        // FIXME WOWL: make an owl nav/tabs component so we don't have to do this
        const activeNavItem = ul.querySelector(".nav-link.active").parentElement;
        const index = [...ul.children].indexOf(activeNavItem);
        this.props.applyExamples(index);
        this.close();
    }
}
KanbanColumnExamplesDialog.bodyTemplate = "web.KanbanColumnExamplesDialog";
KanbanColumnExamplesDialog.footerTemplate = "web.KanbanColumnExamplesDialogFooter";
KanbanColumnExamplesDialog.title = _lt("Kanban Examples");
KanbanColumnExamplesDialog.contentClass = "o_kanban_examples_dialog";
