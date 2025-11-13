import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { Domain } from "@web/core/domain";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { useService } from "@web/core/utils/hooks";

/**
 * Option Component to enable the user to filter some snippets to a specific subset of ids following
 * a domain.
 */
export class SnippetVisibilityOption extends BaseOptionComponent {
    static template = "mass_mailing.VisibilityOption";
    static selector = "section";
    static dependencies = ["mass_mailing.SnippetVisibility"];

    setup() {
        super.setup();
        this.getModel = this.dependencies["mass_mailing.SnippetVisibility"].getModel;
        this.treeProcessor = useService("tree_processor");
        this.dialog = useService("dialog");
        this.historyPlugin = this.env.editor.shared.history;
        this.overlayButtonsPlugin = this.env.editor.shared.overlayButtons;

        this.state = useDomState((editingElement) => {
            const currentDomain = new Domain(
                JSON.parse(editingElement.dataset.filterDomain || "[]")
            );
            this.parseTree(currentDomain);
            return {
                domain: currentDomain,
            };
        });
    }

    get stringifiedDomain() {
        return JSON.stringify(this.state.domain.toJson());
    }

    /**
     *
     * @param {import("@web/core/tree_editor/condition_tree").Tree} tree
     */
    async parseTree(domain) {
        const resModel = this.getModel();
        const tree = await this.treeProcessor.treeFromDomain(resModel, domain, !this.env.debug);
        // Extract subtrees connected by an `&`, Odoo Standard for domain facets
        const trees = !tree.negate && tree.value === "&" ? tree.children : [tree];
        this.state.facets = await Promise.all(
            trees.map((tree) =>
                this.treeProcessor.getDomainTreeDescription(resModel, tree, false, 2, 1)
            )
        );
    }

    onClickEditDomain() {
        this.overlayButtonsPlugin.hideOverlayButtonsUi();
        this.dialog.add(
            DomainSelectorDialog,
            {
                resModel: this.getModel(),
                domain: this.state.domain.toString(),
                isDebugMode: !!this.env.debug,
                onConfirm: (domain) => {
                    const newDomain = new Domain(domain);
                    this.state.domain = newDomain;
                    this.env.getEditingElement().dataset.filterDomain = JSON.stringify(
                        this.state.domain.toJson()
                    );
                    this.parseTree(newDomain);
                    this.config.onChange?.({ isPreviewing: false });
                },
            },
            {
                onClose: () => {
                    this.overlayButtonsPlugin.showOverlayButtonsUi();
                },
            }
        );
    }
}
