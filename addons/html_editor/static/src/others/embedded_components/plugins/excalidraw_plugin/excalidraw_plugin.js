import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { ExcalidrawDialog } from "@html_editor/others/embedded_components/plugins/excalidraw_plugin/excalidraw_dialog/excalidraw_dialog";

export class ExcalidrawPlugin extends Plugin {
    static id = "excalidraw";
    static dependencies = ["embeddedComponents", "dom", "selection", "link", "history"];
    resources = {
        user_commands: [
            {
                id: "insertDrawingBoard",
                title: _t("Drawing Board"),
                description: _t("Insert an Excalidraw Board"),
                icon: "fa-pencil-square-o",
                run: this.insertDrawingBoard.bind(this),
            },
        ],
        powerbox_items: [
            {
                categoryId: "navigation",
                commandId: "insertDrawingBoard",
            },
        ],
    };

    insertDrawingBoard() {
        const selection = this.dependencies.selection.getEditableSelection();
        let restoreSelection = () => {
            this.dependencies.selection.setSelection(selection);
        };
        this.services.dialog.add(
            ExcalidrawDialog,
            {
                saveLink: (href) => {
                    const templateBlock = renderToElement(
                        "html_editor.EmbeddedExcalidrawBlueprint",
                        {
                            embeddedProps: JSON.stringify({ source: href }),
                        },
                        {
                            document: this.document,
                        }
                    );
                    this.dependencies.dom.insert(templateBlock);
                    this.dependencies.history.addStep();

                    restoreSelection = () => {};
                },
            },
            { onClose: () => restoreSelection() }
        );
    }
}
