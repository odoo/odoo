import { HtmlViewer } from "@html_editor/fields/html_viewer";
import { LocalOverlayContainer } from "@html_editor/local_overlay_container";
import { usePositionHook } from "@html_editor/position_hook";
import { onWillDestroy, useEffect, useExternalListener, useState, useSubEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { KnowledgeCommentsHandler } from "@knowledge/comments/comments_handler/comments_handler";
import { CommentBeaconManager } from "@knowledge/comments/comment_beacon_manager";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { uniqueId } from "@web/core/utils/functions";
import { effect } from "@web/core/utils/reactive";
import { batched } from "@web/core/utils/timing";

export class KnowledgeHtmlViewer extends HtmlViewer {
    static template = "knowledge.KnowledgeHtmlViewer";
    static components = {
        ...HtmlViewer.components,
        LocalOverlayContainer,
    };

    setup() {
        super.setup();
        this.commentsService = useService("knowledge.comments");
        this.commentsState = useState(this.commentsService.getCommentsState());
        let editorThreadsKeys;
        this.alive = true;
        useExternalListener(window, "click", this.onWindowClick);
        effect(
            batched((state) => {
                if (!this.alive) {
                    return;
                }
                const editorThreads = state.editorThreads;
                const keys = Object.keys(editorThreads).toString();
                if (keys !== editorThreadsKeys) {
                    this.commentBeaconManager?.sortThreads();
                    this.commentBeaconManager?.drawThreadOverlays();
                    editorThreadsKeys = keys;
                }
            }),
            [this.commentsState]
        );
        onWillDestroy(() => {
            this.alive = false;
        });
        this.overlayRef = useChildRef();
        useSubEnv({
            localOverlayContainerKey: uniqueId("html_viewer"),
        });
        usePositionHook(this.readonlyElementRef, document, () => {
            this.commentBeaconManager?.drawThreadOverlays();
            this.props.config.onLayoutGeometryChange?.();
        });
        this.overlayComponentsKey = uniqueId("KnowledgeCommentsHandler");
        useEffect(
            // TODO ABD: investigate if we need useRecordObserver if user_permission changes ?
            // maybe patch occurs too late when user_permission change ?
            // is it even necessary to check for permission = "none" ?
            () => {
                let overlayContainer;
                if (
                    this.readonlyElementRef.el &&
                    this.overlayRef.el &&
                    this.env.model.root.data.user_permission &&
                    this.env.model.root.data.user_permission !== "none"
                ) {
                    overlayContainer = this.makeLocalOverlay();
                    this.overlayRef.el.append(overlayContainer);
                    // reactive on this object if necessary
                    this.commentBeaconManager = new CommentBeaconManager({
                        document,
                        source: this.readonlyElementRef.el,
                        overlayContainer: overlayContainer,
                        commentsState: this.commentsState,
                        readonly: true,
                    });
                    this.commentBeaconManager.sortThreads();
                    this.commentBeaconManager.drawThreadOverlays();
                    registry
                        .category(this.env.localOverlayContainerKey)
                        .add(this.overlayComponentsKey, {
                            Component: KnowledgeCommentsHandler,
                            props: {
                                commentBeaconManager: this.commentBeaconManager,
                                contentRef: this.readonlyElementRef,
                            },
                        });
                }
                return () => {
                    overlayContainer?.remove();
                    this.commentBeaconManager?.destroy();
                    this.commentBeaconManager = undefined;
                    registry
                        .category(this.env.localOverlayContainerKey)
                        .remove(this.overlayComponentsKey);
                    this.overlayComponentsKey = uniqueId("KnowledgeCommentsHandler");
                };
            },
            () => [this.readonlyElementRef.el, this.overlayRef.el, this.state.value]
        );
    }

    onWindowClick(ev) {
        const selector = ".oe-local-overlay, .o_knowledge_comment_box";
        const closestElement = ev.target.closest(selector);
        if (!closestElement) {
            this.commentsState.activeThreadId = undefined;
        }
    }

    makeLocalOverlay() {
        const overlayContainer = document.createElement("div");
        overlayContainer.className = `oe-local-overlay`;
        overlayContainer.setAttribute("data-oe-local-overlay-id", "KnowledgeThreadBeacons");
        return overlayContainer;
    }
}
