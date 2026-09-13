// @ts-check
/** @odoo-module native */

import { onMounted, status, useComponent, useEffect } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";

const log = makeLogger("web.components.code_editor");

/**
 * @typedef {{ row: number, column: number }} CursorPosition
 * @typedef AceEditorParams
 * @property {{ el: HTMLElement | null }} ref
 * @property {() => string} getValue
 * @property {() => string | number} getSessionId
 * @property {() => string | undefined} getMode
 * @property {() => string | undefined} getTheme
 * @property {() => boolean} isReadonly
 * @property {() => boolean} showLineNumbers
 * @property {() => number | undefined} getMaxLines
 * @property {(value: string, cursor: CursorPosition) => void} onChange
 * @property {() => void} [onBlur]
 * @property {(modeId: string | undefined) => void} [onModeChanged]
 * @property {CursorPosition} [initialCursorPosition]
 */

export class AceEditorController {
    /** @param {AceEditorParams} params */
    constructor(params) {
        this.params = params;
        /** @type {Record<string | number, any>} */
        this.sessions = Object.create(null);
        /** @type {any} */
        this.editor = null;
        this.ignoreAceChange = false;
        this.onSessionChange = () => {
            if (!this.ignoreAceChange && this.editor) {
                this.params.onChange(
                    this.editor.getValue(),
                    this.editor.getCursorPosition(),
                );
            }
        };
    }

    /**
     * @param {HTMLElement} el
     * @returns {() => void}
     */
    attach(el) {
        const editor = window.ace.edit(el);
        this.editor = editor;
        editor.setOptions({ showPrintMargin: false, useWorker: false });
        editor.$blockScrolling = true;
        editor.on("changeMode", () =>
            this.params.onModeChanged?.(editor.getSession().$modeId.split("/").at(-1)),
        );
        editor.on("blur", () => this.params.onBlur?.());

        const session = editor.getSession();
        this.sessions[this.params.getSessionId()] ??= session;
        session.setValue(this.params.getValue());
        session.on("change", this.onSessionChange);

        return () => this.detach();
    }

    detach() {
        this.editor?.destroy();
        this.editor = null;
        for (const sessionId of Object.keys(this.sessions)) {
            this.sessions[sessionId].destroy?.();
            delete this.sessions[sessionId];
        }
    }

    /** @param {string | undefined} theme */
    applyTheme(theme) {
        this.editor?.setTheme(theme ? `ace/theme/${theme}` : "");
    }

    /**
     * @param {boolean} readonly
     * @param {boolean} showLineNumbers
     * @param {number | undefined} maxLines
     */
    applyOptions(readonly, showLineNumbers, maxLines) {
        if (!this.editor) {
            return;
        }
        this.editor.setOptions({
            readOnly: readonly,
            highlightActiveLine: !readonly,
            highlightGutterLine: !readonly,
            maxLines,
        });
        this.editor.renderer.setOptions({
            displayIndentGuides: !readonly,
            showGutter: !readonly && showLineNumbers,
        });
        this.editor.renderer.$cursorLayer.element.style.display = readonly
            ? "none"
            : "block";
    }

    /**
     * @param {string | number} sessionId
     * @returns {any}
     */
    acquireSession(sessionId) {
        log.logic("acquire session", () => ({
            cached: Object.hasOwn(this.sessions, sessionId),
        }));
        if (!this.sessions[sessionId]) {
            const session = new window.ace.EditSession(this.params.getValue());
            session.setUndoManager(new window.ace.UndoManager());
            session.setOptions({ useWorker: false, tabSize: 2, useSoftTabs: true });
            session.on("change", this.onSessionChange);
            this.sessions[sessionId] = session;
        }
        return this.sessions[sessionId];
    }

    /**
     * @param {string | number} sessionId
     * @param {string | undefined} mode
     */
    showSession(sessionId, mode) {
        if (!this.editor) {
            return;
        }
        const session = this.acquireSession(sessionId);
        session.setMode(mode ? `ace/mode/${mode}` : "");
        this.editor.setSession(session);
    }

    /**
     * @param {string | number} sessionId
     * @param {string} value
     */
    syncValue(sessionId, value) {
        const session = this.sessions[sessionId];
        if (!session || session.getValue() === value) {
            return;
        }
        this.ignoreAceChange = true;
        session.setValue(value);
        this.ignoreAceChange = false;
    }

    /** @param {CursorPosition} position */
    placeCursor(position) {
        if (!this.editor) {
            return;
        }
        this.editor.focus();
        const pos = { row: position.row || 0, column: position.column || 0 };
        this.editor.selection.moveToPosition(pos);
        this.editor.renderer.scrollCursorIntoView(pos, 0.5);
    }
}

/**
 * @param {AceEditorParams} params
 * @returns {AceEditorController}
 */
export function useAceEditor(params) {
    const component = useComponent();
    const controller = new AceEditorController(params);

    useEffect(
        (el) => (el ? controller.attach(el) : undefined),
        () => [params.ref.el],
    );
    useEffect(
        (theme) => controller.applyTheme(theme),
        () => [params.getTheme()],
    );
    useEffect(
        (readonly, lineNumbers, maxLines) =>
            controller.applyOptions(readonly, lineNumbers, maxLines),
        () => [params.isReadonly(), params.showLineNumbers(), params.getMaxLines()],
    );
    useEffect(
        (sessionId, mode) => controller.showSession(sessionId, mode),
        () => [params.getSessionId(), params.getMode()],
    );
    useEffect(
        (sessionId, value) => controller.syncValue(sessionId, value),
        () => [params.getSessionId(), params.getValue()],
    );

    const { initialCursorPosition } = params;
    if (initialCursorPosition) {
        onMounted(() => {
            browser.requestAnimationFrame(() => {
                if (status(component) !== "destroyed") {
                    controller.placeCursor(initialCursorPosition);
                }
            });
        });
    }

    return controller;
}
