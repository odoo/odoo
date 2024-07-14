/** @odoo-module */

import { WithSearch } from "@web/search/with_search/with_search";
import { cleanClickedElements } from "@web_studio/client_action/view_editor/editors/utils";
import { Component, onError, onMounted, toRaw, useRef, xml, useSubEnv, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const HEIGHT = "height: 100%;";

export class StudioView extends Component {
    static props = { autoClick: { type: Function, optional: true }, "*": true }; // Same as View.js. This is just a wrapper
    setup() {
        this.notification = useService("notification");
        this.style = this.props.setOverlay ? `pointer-events: none; ${HEIGHT}` : HEIGHT;
        this.withSearchProps = {
            resModel: this.props.resModel,
            SearchModel: this.props.SearchModel,
            context: this.props.context,
            domain: this.props.domain,
            globalState: this.props.globalState,
            searchViewArch: this.props.searchViewArch,
            searchViewFields: this.props.searchViewFields,
            irFilters: this.props.searchViewIrFilters,
            display: this.props.display,
        };
        this.viewEditorModel = this.env.viewEditorModel;

        this.viewRenderer = useRef("viewRenderer");

        this.controllerProps = { ...this.viewEditorModel.controllerProps };

        useEffect(
            (xpath) => {
                if (xpath) {
                    this.updateActiveNode({ xpath, resetSidebarOnNotFound: true });
                }
            },
            () => [this.viewEditorModel.activeNodeXpath]
        );

        const rawModel = toRaw(this.viewEditorModel);
        useEffect(
            () => {
                rawModel.isInEdition = false;
            },
            () => [rawModel.isInEdition]
        );

        onError((error) => {
            if (rawModel.isInEdition) {
                this.notification.add(
                    _t(
                        "The requested change caused an error in the view. It could be because a field was deleted, but still used somewhere else."
                    ),
                    {
                        type: "danger",
                        title: _t("Error"),
                    }
                );
                this.viewEditorModel.resetSidebar("view");
                this.viewEditorModel._operations.undo(false);
            } else {
                throw error;
            }
        });

        const config = {
            ...this.env.config,
            onNodeClicked: (xpath) => {
                if (this.updateActiveNode({ xpath })) {
                    this.viewEditorModel.activeNodeXpath = xpath;
                }
            },
        };

        if (this.props.autoClick) {
            onMounted(() => this.props.autoClick());
        }

        useSubEnv({
            config,
            __beforeLeave__: null,
            __getGlobalState__: null,
            __getLocalState__: null,
            __getContext__: null,
            __getOrderBy__: null,
        });
    }

    updateActiveNode({ xpath, resetSidebarOnNotFound = false }) {
        const vem = this.env.viewEditorModel;
        cleanClickedElements(this.viewRenderer.el);
        const el = this.viewRenderer.el.querySelector(
            `[data-studio-xpath="${xpath}"], [studioxpath="${xpath}"]`
        );
        if (!el) {
            if (resetSidebarOnNotFound) {
                vem.resetSidebar();
            }
            return false;
        }
        if (vem.editorInfo.editor.styleClickedElement) {
            vem.editorInfo.editor.styleClickedElement(this.viewRenderer, { xpath });
            return true;
        }
        const clickable = el.closest(".o-web-studio-editor--element-clickable");
        if (clickable) {
            clickable.classList.add("o-web-studio-editor--element-clicked");
        }
        return true;
    }
}
StudioView.components = { WithSearch };
StudioView.template = xml`
    <div t-att-style="style" class="w-100" t-ref="viewRenderer">
        <WithSearch t-props="withSearchProps" t-slot-scope="search">
            <t t-component="viewEditorModel.editorInfo.editor.Controller" t-props="Object.assign(controllerProps, search)" />
        </WithSearch>
    </div>
`;
