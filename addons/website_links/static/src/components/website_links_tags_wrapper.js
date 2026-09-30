import { Component, onWillStart, useState } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useService } from "@web/core/utils/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class WebsiteLinksTagsWrapper extends Component {
    static template = "website_links.WebsiteLinksTagsWrapper";
    static components = { SelectMenu, DropdownItem };
    static props = {
        placeholder: { optional: true, type: String },
        model: { optional: true, type: String },
    };

    setup() {
        this.orm = useService("orm");
        this.keepLast = new KeepLast();
        this.state = useState({
            placeholder: this.props.placeholder,
            choices: [],
            value: undefined,
        });
        onWillStart(async () => {
            this.canCreateLinkTracker = await this.orm.call(this.props.model, "has_access", [
                [],
                "create",
            ]);
            await this.loadChoice();
        });
    }

    get showCreateOption() {
        return (
            this.select.data.searchValue &&
            !this.state.choices.some((c) => c.label === this.select.data.searchValue) &&
            this.canCreateLinkTracker
        );
    }

    onSelect(value) {
        this.state.value = value;
    }

    async onCreateOption(string, closeFn) {
        const record = await this.orm.call("utm.mixin", "find_or_create_record", [
            this.props.model,
            string,
        ]);
        const choice = {
            label: record.name,
            value: record.id,
        };
        this.state.choices.push(choice);
        this.onSelect(choice.value);
    }

    loadChoice(searchString = "") {
        return new Promise((resolve, reject) => {
            // We want to search with a limit and not care about any
            // pagination implementation. To make this work, we
            // display the exact match first though, which requires
            // an extra RPC (could be refactored into a new
            // controller in master but... see TODO).
            // TODO at some point this whole app will be moved as a
            // backend screen, with real m2o fields etc... in which
            // case the "exact match" feature should be handled by
            // the ORM somehow ?
            const limit = 100;
            const searchReadParams = [
                ["id", "name"],
                {
                    limit: limit,
                    order: "name, id desc", // Allows to have exact match first
                },
            ];
            const proms = [];
            proms.push(
                this.orm.searchRead(
                    this.props.model,
                    // Exact match + results that start with the search
                    [["name", "=ilike", `${searchString}%`]],
                    ...searchReadParams
                )
            );
            proms.push(
                this.orm.searchRead(
                    this.props.model,
                    // Results that contain the search but do not start
                    // with it
                    [["name", "=ilike", `%_${searchString}%`]],
                    ...searchReadParams
                )
            );
            // Keep last is there in case a RPC takes longer than
            // the debounce delay + next rpc delay for some reason.
            this.keepLast
                .add(Promise.all(proms))
                .then(([startingMatches, endingMatches]) => {
                    const formatChoice = (choice) => {
                        choice.value = choice.id;
                        choice.label = choice.name;
                        return choice;
                    };
                    startingMatches.map(formatChoice);

                    // We loaded max a 2 * limit amount of records but
                    // ensure that we do not display "ending matches" if
                    // we may not have loaded all "starting matches".
                    if (startingMatches.length < limit) {
                        const startingMatchesId = startingMatches.map((value) => value.id);
                        const extraEndingMatches = endingMatches.filter(
                            (value) => !startingMatchesId.includes(value.id)
                        );
                        extraEndingMatches.map(formatChoice);
                        return startingMatches.concat(extraEndingMatches);
                    }
                    // In that case, we made one RPC too much but this
                    // was chosen over not making them go in parallel.
                    // We don't want to display "ending matches" if not
                    // all "starting matches" have been loaded.
                    return startingMatches;
                })
                .then((result) => {
                    this.state.choices = result;
                    resolve();
                })
                .catch(reject);
        });
    }
}
