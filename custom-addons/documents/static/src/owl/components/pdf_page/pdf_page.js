/** @odoo-module **/

import { Component, onMounted, onPatched, useState, useRef } from "@odoo/owl";

/**
 * Represents the page of a PDF.
 */
export class PdfPage extends Component {
    static defaultProps = {
        isPreview: false,
        isSelected: false,
    };
    static props = {
        canvas: { type: Object, optional: true },
        isPreview: { type: Boolean, optional: true },
        isSelected: { type: Boolean, optional: true },
        isFocused: { type: Boolean, optional: true },
        onPageClicked: { type: Function, optional: true },
        onPageDragged: { type: Function, optional: true },
        onPageDropped: { type: Function, optional: true },
        onSelectClicked: { type: Function, optional: true },
        toRender: { type: Boolean, optional: true },
        pageId: String,
    };
    static template = "documents.component.PdfPage";

    setup() {
        this.state = useState({
            isHover: false,
        });
        // Used to append a canvas when it has been rendered.
        this.canvasWrapperRef = useRef("canvasWrapper");
        this.isRendered = false;

        onMounted(() => this.renderPage(this.props.canvas));
        onPatched(() => this.renderPage(this.props.canvas));
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * The canvas is rendered asynchronously so it is only manually appended
     * later when available. It should have been done through the natural owl
     * re-rendering but it is currently causing unnecessary re-renderings of
     * sibling components which would noticeably slows the behaviour down.
     *
     * @public
     * @param {DomElement} canvas
     */
    renderPage(canvas) {
        if (this.props.toRender) {
            this.isRendered = false;
        }
        if (!canvas || this.isRendered) {
            return;
        }
        this.canvasWrapperRef.el.querySelector(".o_documents_pdf_canvas")?.remove();
        this.canvasWrapperRef.el.appendChild(canvas);
        this.isRendered = true;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @public
     * @param {MouseEvent} ev
     */
    onClickWrapper(ev) {
        if (this.props.onPageClicked) {
            this.props.onPageClicked(this.props.pageId);
        }
    }
    /**
     * @public
     * @param {MouseEvent} ev
     */
    onClickSelect(ev) {
        if (this.props.onSelectClicked) {
            this.props.onSelectClicked(this.props.pageId, ev.shiftKey, ev.ctrlKey || ev.metaKey);
        }
    }
    /**
     * @public
     * @param {MouseEvent} ev
     */
    onDragEnter(ev) {
        ev.preventDefault();
        this.state.isHover = true;
    }
    /**
     * @public
     * @param {MouseEvent} ev
     */
    onDragLeave(ev) {
        ev.preventDefault();
        this.state.isHover = false;
    }
    /**
     * @public
     * @param {MouseEvent} ev
     */
    onDragOver(ev) {
        ev.preventDefault();
    }
    /**
     * @public
     * @param {MouseEvent} ev
     */
    onDragStart(ev) {
        if (this.props.onPageDragged) {
            this.props.onPageDragged(ev);
        }
        ev.dataTransfer.setData("o_documents_pdf_data", this.props.pageId);
    }
    /**
     * @public
     * @param {MouseEvent} ev
     */
    onDrop(ev) {
        this.state.isHover = false;
        if (!ev.dataTransfer.types.includes("o_documents_pdf_data")) {
            return;
        }
        const pageId = ev.dataTransfer.getData("o_documents_pdf_data");
        if (pageId === this.props.pageId) {
            return;
        }
        if (this.props.onPageDropped) {
            this.props.onPageDropped(this.props.pageId, pageId);
        }
    }
}
