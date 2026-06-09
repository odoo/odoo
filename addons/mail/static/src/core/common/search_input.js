import { SearchState } from "@mail/utils/common/hooks";

import { Component, props, signal, types, useEffect } from "@odoo/owl";

import { useAutofocus } from "@web/core/utils/hooks";

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
 */
export class SearchInput extends Component {
    static template = "mail.SearchInput";

    setup() {
        super.setup();
        this.props = props(
            {
                "accesskey?": types.string(),
                /** @type {boolean | Parameters<typeof useAutofocus>[0]} */
                "autofocus?": types.or([types.boolean(), types.object()]),
                "classNames?": types.string(),
                "inputRef?": types.signal(types.instanceOf(HTMLElement)),
                "loadingDelay?": types.number(),
                "onClear?": types.function([types.instanceOf(MouseEvent)]),
                "onKeydown?": types.function([types.instanceOf(KeyboardEvent)]),
                "placeholder?": types.string(),
                search: types.instanceOf(SearchState),
            },
            {
                autofocus: false,
                inputRef: signal(null, { type: types.instanceOf(HTMLElement) }),
                loadingDelay: 200,
            }
        );
        this.uniqueId = `mail.SearchInput.${nextId++}`;
        this.spinner = signal(false);
        useEffect(() => {
            if (!this.props.search.loading) {
                this.spinner.set(false);
                return;
            }
            const timer = setTimeout(() => this.spinner.set(true), this.props.loadingDelay);
            return () => clearTimeout(timer);
        });
        if (this.props.autofocus) {
            const opts = typeof this.props.autofocus === "object" ? this.props.autofocus : {};
            useAutofocus({ ...opts, ref: this.props.inputRef });
        }
    }
}
