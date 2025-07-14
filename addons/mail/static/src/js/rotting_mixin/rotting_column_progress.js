import { ColumnProgress } from "@web/views/view_components/column_progress";

export class RottingColumnProgress extends ColumnProgress {
    static template = "mail.RottingColumnProgress";
    static props = {
        ...ColumnProgress.props,
        progressBarState: { type: Object },
    };

    setup() {
        super.setup();
        const rottingFilter = Object.values(this.env.searchModel.searchItems).find(
            (filter) =>
                filter.name === "filter_rotting" || filter.domain === "[('is_rotting', '=', True)]"
        );
        this.rottingFilterAvailable = !!rottingFilter;
    }

    getRottingGroupCount(group) {
        const isRottingField = group._config.fields.is_rotting;
        if (!isRottingField) {
            return {};
        }
        return {
            title: isRottingField.string,
            value: group.list.records.filter((record) => record.data.is_rotting).length,
        };
    }

    /**
     * Checks that a filter verifying rotting status exists for the current set view.
     * If that filter exists, it is toggled.
     */
    async onRotIconClick() {
        const rottingFilter = Object.values(this.env.searchModel.searchItems).find(
            (filter) =>
                filter.name === "filter_rotting" || filter.domain === "[('is_rotting', '=', True)]"
        );
        if (rottingFilter) {
            this.env.searchModel.toggleSearchItem(rottingFilter.id);
        }
    }
}
