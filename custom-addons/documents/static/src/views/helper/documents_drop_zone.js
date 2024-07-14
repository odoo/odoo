/** @odoo-module **/

import { Component, useEffect, useState } from "@odoo/owl";

export class DocumentsDropZone extends Component {
    static props = [
        "parentRoot", // Parent's root element, used to know the zone to use.
    ];

    setup() {
        this.state = useState({
            dragOver: false,
            topOffset: 0,
        });
        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                this.state.topOffset = el.scrollTop;
                const overHandler = this.onDragOver.bind(this);
                const leaveHandler = this.onDragLeave.bind(this);
                const scrollHandler = () => {
                    this.state.topOffset = el.scrollTop;
                };
                el.addEventListener("dragover", overHandler);
                el.addEventListener("dragleave", leaveHandler);
                el.addEventListener("scroll", scrollHandler);
                return () => {
                    el.removeEventListener("dragover", overHandler);
                    el.removeEventListener("dragleave", leaveHandler);
                    el.removeEventListener("scroll", scrollHandler);
                };
            },
            () => [this.props.parentRoot.el]
        );
    }

    get root() {
        return this.props.parentRoot;
    }

    get isFolder() {
        return !!this.env.searchModel.getSelectedFolderId();
    }

    get rootDropOverClass() {
        return this.isFolder ? "o_documents_drop_over" : "o_documents_drop_over_unauthorized";
    }

    onDragOver(ev) {
        if (
            !ev.dataTransfer.types.includes("Files") ||
            ev.dataTransfer.types.includes("o_documents_data")
        ) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();

        this.root?.el?.classList.toggle(this.rootDropOverClass, true);
        this.state.dragOver = true;
    }

    onDragLeave(ev) {
        ev.stopPropagation();
        ev.preventDefault();

        this.root?.el?.classList.remove(this.rootDropOverClass);
        this.state.dragOver = false;
    }

    onDrop(ev) {
        if (!ev.dataTransfer.types.includes("Files")) {
            return;
        }

        this.root?.el?.classList.remove(this.rootDropOverClass);
        this.state.dragOver = false;
        if (this.isFolder) {
            this.env.documentsView.bus.trigger("documents-upload-files", {
                files: ev.dataTransfer.files,
                folderId: this.env.searchModel.getSelectedFolderId(),
                recordId: false,
                tagIds: this.env.searchModel.getSelectedTagIds(),
            });
        }
    }
}
DocumentsDropZone.template = "documents.DocumentsDropZone";
