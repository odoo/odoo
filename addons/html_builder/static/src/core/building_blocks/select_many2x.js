import { Component, useState, onWillUpdateProps, onWillDestroy } from "@odoo/owl";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { useCachedModel } from "@html_builder/core/cached_model_utils";
import { _t } from "@web/core/l10n/translation";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useDropdownCloser } from "@web/core/dropdown/dropdown_hooks";
import { shallowEqual } from "@web/core/utils/arrays";

class SelectMany2XCreate extends Component {
    static template = "html_builder.SelectMany2XCreate";
    static props = {
        name: String,
        create: Function,
    };

    setup() {
        this.dropdown = useDropdownCloser();
        this.create = this.create.bind(this);
    }

    create() {
        this.dropdown.close();
        this.props.create(this.props.name);
    }
}

export class SelectMany2X extends Component {
    static template = "html_builder.SelectMany2X";
    static props = {
        model: String,
        fields: { type: Array, element: String, optional: true },
        domain: { type: Array, optional: true },
        limit: { type: Number, optional: true },
        selected: {
            type: Array,
            element: { type: Object, shape: { id: [Number, String], "*": true } },
        },
        select: Function,
        preview: { type: Function, optional: true },
        revert: { type: Function, optional: true },
        closeOnEnterKey: { type: Boolean, optional: true },
        message: { type: String, optional: true },
        create: { type: Function, optional: true },
        nullText: { type: String, optional: true },
    };
    static defaultProps = {
        fields: [],
        domain: [],
        limit: 5,
        closeOnEnterKey: true,
        message: _t("Choose a record..."),
    };
    static components = { SelectMenu, SelectMany2XCreate };

    setup() {
        this.orm = useService("orm");
        this.cachedModel = useCachedModel();
        this.prevSelectedIds = undefined;
        this.prevSearchValue = undefined;
        this.state = useState({
            nameToCreate: "",
            searchResults: [],
            limit: this.props.limit,
        });
        onWillUpdateProps(async (newProps) => {
            if (this.searchInvalidationKey(this.props) !== this.searchInvalidationKey(newProps)) {
                this.prevSelectedIds = undefined;
                this.prevSearchValue = undefined;
                this.state.searchResults = [];
            }
        });
        this.menuRef = useChildRef();
        onWillDestroy(() => this.removeListeners?.());
    }
    onOpened() {
        const menuEl = this.menuRef.el;
        if (menuEl) {
            this.removeListeners?.();
            const onNavigatedAway = this.onNavigatedAway.bind(this);
            const onNavigatedBack = this.onNavigatedBack.bind(this);
            menuEl.addEventListener("pointerleave", onNavigatedAway);
            menuEl.addEventListener("pointerenter", onNavigatedBack);
            this.removeListeners = () => {
                delete this.removeListeners;
                menuEl.removeEventListener("pointerleave", onNavigatedAway);
                menuEl.removeEventListener("pointerenter", onNavigatedBack);
            };
        }
    }
    onClosed() {
        this.removeListeners?.();
        this.onNavigatedAway();
    }
    searchInvalidationKey(props) {
        return JSON.stringify([props.model, props.fields, props.domain]);
    }
    searchMore(searchValue) {
        this.state.limit += this.props.limit;
        this.search(searchValue);
    }
    async search(searchValue) {
        const domain = Object.values(this.props.domain).filter((item) => item !== null);
        const selectedIds = this.props.selected.map((e) => e.id);
        if (selectedIds.length) {
            domain.push(["id", "not in", selectedIds]);
        }
        const tuples = await this.orm.call(this.props.model, "name_search", [], {
            name: searchValue,
            domain: domain,
            operator: "ilike",
            limit: this.state.limit + 1,
        });
        this.state.hasMore = tuples.length > this.state.limit;
        const results = await this.cachedModel.ormRead(
            this.props.model,
            tuples.map(([id, _name]) => id),
            [...new Set(this.props.fields).add("display_name").add("name")]
        );
        if (this.props.nullText && (!results.length || results[0].id)) {
            results.unshift({
                id: 0,
                name: this.props.nullText,
                display_name: this.props.nullText,
            });
        }
        this.state.searchResults = results;
    }
    filteredSearchResult() {
        const selectedIds = new Set(this.props.selected.map((e) => e.id));
        return this.state.searchResults
            .filter((entry) => !selectedIds.has(entry.id))
            .slice(0, this.state.limit);
    }
    async canCreate(name) {
        if (!this.props.create || !name.length) {
            return false;
        }
        const allRecords = await this.cachedModel.ormSearchRead(
            this.props.model,
            [],
            ["id", "name"]
        );
        const usedNames = [
            // Exclude existing names
            ...allRecords.map((item) => item.name),
            // Exclude new names
            ...this.props.selected.map((item) => item.name),
        ];
        return !usedNames.includes(name);
    }
    async onInput(searchValue) {
        const selectedIds = this.props.selected.map((e) => e.id);
        // Avoid redundant search queries when the user toggles the dropdown
        // without changing the search value or the selected options.
        if (
            searchValue === this.prevSearchValue &&
            shallowEqual(selectedIds, this.prevSelectedIds)
        ) {
            return;
        }
        this.prevSearchValue = searchValue;
        this.prevSelectedIds = selectedIds;
        await this.search(searchValue);
        this.state.nameToCreate = (await this.canCreate(searchValue)) ? searchValue : "";
    }

    preview(value) {
        if (this.previewed !== value) {
            this.previewed = value;
            this.props.preview?.(value);
        }
    }
    revert() {
        delete this.previewed;
        this.props.revert?.();
    }
    onNavigated(choice) {
        choice ? this.preview(choice.value) : this.revert();
        delete this.lastPreviewed;
    }
    onNavigatedAway() {
        if ("previewed" in this) {
            this.lastPreviewed = this.previewed;
            this.revert();
        }
    }
    onNavigatedBack() {
        if ("lastPreviewed" in this) {
            this.preview(this.lastPreviewed);
        }
    }
}
