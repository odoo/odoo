import { useDebounced } from "@web/core/utils/timing";
import { useAutofocus } from "@web/core/utils/hooks";

import { Component, xml, useEffect, useState } from "@odoo/owl";

export class SearchMedia extends Component {
    static template = xml`
        <div class="position-relative mw-lg-25 flex-grow-1 me-auto">
            <input type="text" class="o_we_search o_input form-control" t-att-placeholder="props.searchPlaceholder.trim()" t-model="state.input" t-ref="autofocus"/>
            <i class="oi oi-search input-group-text position-absolute end-0 top-50 me-n3 px-2 py-1 translate-middle bg-transparent border-0" title="Search" role="img" aria-label="Search"/>
        </div>`;
    static props = ["searchPlaceholder", "search", "needle"];
    setup() {
        useAutofocus({ mobile: true });
        this.debouncedSearch = useDebounced(this.props.search, 1000);

        this.state = useState({
            input: this.props.needle || "",
        });

        useEffect(
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
