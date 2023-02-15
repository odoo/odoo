/** @odoo-module **/

import { debounce } from '@web/core/utils/timing';
import { useAutofocus } from '@web/core/utils/hooks';

import { Component, onWillUnmount, xml } from "@odoo/owl";

export class SearchMedia extends Component {
    setup() {
        useAutofocus();
        this.search = debounce((ev) => this.props.search(ev.target.value), 1000);
        onWillUnmount(() => {
            this.search.cancel();
        });
    }
}
SearchMedia.template = xml`
<div class="position-relative mw-lg-25 flex-grow-1 me-auto">
    <input type="text" class="o_we_search o_input form-control" t-att-placeholder="props.searchPlaceholder.trim()" t-att-value="props.needle" t-on-input="search" t-ref="autofocus"/>
    <i class="oi oi-search input-group-text position-absolute end-0 top-50 me-n3 px-2 py-1 translate-middle bg-transparent border-0" title="Search" role="img" aria-label="Search"/>
</div>`;
