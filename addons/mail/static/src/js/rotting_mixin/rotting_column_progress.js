import { ColumnProgress } from "@web/views/view_components/column_progress";

export class RottingColumnProgress extends ColumnProgress {
    static template = "mail.RottingColumnProgress";
    static props = {
        ...ColumnProgress.props,
        progressBarState: { type: Object },
        onRotIconClicked: { type: Function },
    };

    getRottingGroupCount(group) {
        const isRottingField = group._config.fields.is_rotting;
        if (!isRottingField) {
            return {};
        }
        const { progressBarState } = this.props;
        const rottingCounts = progressBarState?._pbCounts?.__rotting_counts;
        return {
            title: isRottingField.string,
            value: rottingCounts
                ? rottingCounts[progressBarState._getGroupValue(group)] || 0
                : group.list.records.filter((record) => record.data.is_rotting).length,
        };
    }

    /**
     * Checks that a filter verifying rotting status exists for the current set view.
     * If that filter exists, it is toggled.
     */
    async onRottingIconClick() {
        await this.props.onRotIconClicked(this.props.group);
    }
}
