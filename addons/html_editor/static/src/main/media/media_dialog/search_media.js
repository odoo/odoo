import { useDebounced } from "@web/core/utils/timing";
import { useAutofocus } from "@web/core/utils/hooks";

import { Component, signal, t, useEffect, useProps } from "@odoo/owl";

export class SearchMedia extends Component {
    static template = "html_editor.SearchMedia";
    props = useProps({
        searchPlaceholder: t.string(),
        search: t.function(),
        needle: t.string().optional(),
        delay: t.number().optional(1000),
    });

    input = signal(this.props.needle || "");
    autofocusRef = signal.ref();

    setup() {
        useAutofocus({ ref: this.autofocusRef, mobile: true });
        this.debouncedSearch = useDebounced(this.props.search, this.props.delay);

        useEffect(() => {
            const input = this.input();
            // Do not trigger a search on the initial render.
            if (this.hasRendered) {
                this.debouncedSearch(input);
            } else {
                this.hasRendered = true;
            }
        });
    }
}
