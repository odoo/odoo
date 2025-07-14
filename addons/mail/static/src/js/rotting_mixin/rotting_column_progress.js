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
        if (rottingFilter) {
            this.rottingFilterAvailable = true;
        } else {
            this.rottingFilterAvailable = false;
        }
    }

    getRottingGroupCount(group) {
        const rotField = group._config.fields.is_rotting;
        if (!rotField) {
            return {};
        }
        const rotCount = { title: rotField.string, value: 0 };
        group.list.records.forEach((record) => {
            if (record.data[rotField.name]) {
                rotCount.value++;
            }
        });
        return rotCount;
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
