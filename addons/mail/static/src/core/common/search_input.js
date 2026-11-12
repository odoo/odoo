import { SearchStatePlugin } from "@mail/utils/common/search_state_plugin";

import { Component, signal, t, useEffect, useProps } from "@odoo/owl";

import { autofocusParamsType, useAutofocus } from "@web/core/utils/hooks";

let nextId = 0;

/**
 * Standard search input UI for Discuss: icon prefix that swaps to a spinner
 * while {@link SearchStatePlugin} is loading, with an optional trailing slot for
 * action buttons (e.g. Invite, Create).
 *
 * In the parent's setup, provide the search plugin with `providePlugins`,
 * retrieve its instance with `usePlugin`, and pass it as the `search` prop.
 * This lets the parent read `searchTerm`/`results`/`loading` in its filters,
 * getters, and callbacks.
 *
 */
export class SearchInput extends Component {
    static template = "mail.SearchInput";

    setup() {
        super.setup();
        this.props = useProps({
            accesskey: t.string().optional(),
            /** @type {boolean | Parameters<typeof useAutofocus>[0]} */
            autofocus: t.or([t.boolean(), autofocusParamsType]).optional(false),
            classNames: t.string().optional(""),
            inputClassNames: t.string().optional(""),
            loadingDelay: t.number().optional(200),
            onClear: t.function([t.instanceOf(MouseEvent)]).optional(),
            onKeydown: t.function([t.instanceOf(KeyboardEvent)]).optional(),
            placeholder: t.string().optional(),
            search: t.instanceOf(SearchStatePlugin),
        });
        /** Input element, either owned by the parent (`inputRef` prop) or local. */
        this.inputRef = useProps.static(
            "inputRef",
            t.signal(t.instanceOf(HTMLElement)).optional(() => signal.ref())
        );
        this.uniqueId = `mail.SearchInput.${nextId++}`;
        this.spinner = signal(false);
        useEffect(() => {
            if (!this.props.search.loading()) {
                this.spinner.set(false);
                return;
            }
            const timer = setTimeout(() => this.spinner.set(true), this.props.loadingDelay);
            return () => clearTimeout(timer);
        });
        if (this.props.autofocus) {
            const opts = typeof this.props.autofocus === "object" ? this.props.autofocus : {};
            useAutofocus({ ...opts, ref: this.inputRef });
        }
    }
}
