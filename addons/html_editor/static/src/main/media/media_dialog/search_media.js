import { useLayoutEffect } from "@web/owl2/utils";
import { useDebounced } from "@web/core/utils/timing";
import { useAutofocus } from "@web/core/utils/hooks";

import { Component, proxy } from "@odoo/owl";

export class SearchMedia extends Component {
    static template = "html_editor.SearchMedia";
    static props = ["searchPlaceholder", "search", "needle"];
    setup() {
        useAutofocus({ mobile: true });
        this.debouncedSearch = useDebounced(this.props.search, 1000);

        this.state = proxy({
            input: this.props.needle || "",
        });

        useLayoutEffect(
            (input) => {
                // Do not trigger a search on the initial render.
                if (this.hasRendered) {
                    this.debouncedSearch(input);
                } else {
                    this.hasRendered = true;
                }
            },
            () => [this.state.input]
        );
    }
}
