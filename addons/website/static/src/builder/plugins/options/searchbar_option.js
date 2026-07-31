import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useGetItemValue } from "@html_builder/core/utils";
import { onWillStart, useProps, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class SearchbarOption extends BaseOptionComponent {
    static id = "searchbar_option";
    static template = "website.SearchbarOption";
    props = useProps({
        isMainSearch: t.boolean().optional(false),
    });

    setup() {
        super.setup();
        this.getItemValue = useGetItemValue();
        this.orm = useService("orm");
        this.website = useService("website");

        this.orderByItems = this.getResource("searchbar_option_order_by_items");
        this.searchScopes = [];
        onWillStart(async () => {
            const scopes = await this.orm.cache().call("website", "get_search_scopes", [
                this.website.currentWebsiteId,
            ]);
            this.searchScopes = this.props.isMainSearch
                ? scopes.filter((scope) => scope.allow_main_search)
                : scopes;
        });
    }
}

registry.category("website-options").add(SearchbarOption.id, SearchbarOption);
