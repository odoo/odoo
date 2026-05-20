import { useLayoutEffect, useState } from "@web/owl2/utils";
import { Component } from "@odoo/owl";
import { useAutofocus, useForwardRefToParent } from "@web/core/utils/hooks";

let nextId = 0;

/**
 * Standard search input UI for Discuss: icon prefix that swaps to a spinner
 * while {@link useSearch} is loading, with an optional trailing slot for
 * action buttons (e.g. Invite, Create).
 *
 * The `search` state must be owned by the parent — call `useSearch(...)` in
 * the parent's setup and pass the result here. SearchInput intentionally does
 * not own the hook so parents can read `searchTerm`/`results`/`loading` from
 * their own JS (filters, getters, callbacks) without a forwarding indirection.
 *
 * @typedef {Object} Props
 * @property {ReturnType<typeof import("@mail/utils/common/hooks").useSearch>} search
 * @property {string} [placeholder]
 * @property {boolean | Parameters<typeof useAutofocus>} [autofocus]
 *  When truthy, focuses the input on mount via `useAutofocus`. Pass an object
 *  to forward `mobile`/`selectAll` options.
 * @property {import("@web/core/utils/hooks").Ref} [inputRef] A ref returned by
 *  `useChildRef`, to expose the `<input>` element to the parent (e.g. for popover anchoring).
 * @property {(ev: KeyboardEvent) => void} [onKeydown]
 * @property {string} [classNames] Extra classes for the outer wrapper.
 * @property {number} [loadingDelay=200] Milliseconds the spinner waits before
 *  replacing the search icon. Suppresses flicker on fast local filters.
 * @extends {Component<Props, Env>}
 */
export class SearchInput extends Component {
    static template = "mail.SearchInput";
    static props = {
        search: { type: Object },
        accesskey: { type: String, optional: true },
        autofocus: { type: [Boolean, Object], optional: true },
        classNames: { type: String, optional: true },
        inputRef: { type: Function, optional: true },
        loadingDelay: { type: Number, optional: true },
        onClear: { type: Function, optional: true },
        onKeydown: { type: Function, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = { autofocus: false, loadingDelay: 200 };

    setup() {
        super.setup();
        this.uniqueId = `mail.SearchInput.${nextId++}`;
        this.spinner = useState({ visible: false });
        useLayoutEffect(
            () => {
                if (!this.props.search.loading) {
                    this.spinner.visible = false;
                    return;
                }
                const timer = setTimeout(
                    () => (this.spinner.visible = true),
                    this.props.loadingDelay
                );
                return () => clearTimeout(timer);
            },
            () => [this.props.search.loading]
        );
        this.inputRef = useForwardRefToParent("inputRef");
        if (this.props.autofocus) {
            const opts = typeof this.props.autofocus === "object" ? this.props.autofocus : {};
            useAutofocus({ ...opts, refName: "inputRef" });
        }
    }
}
