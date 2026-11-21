import { ColumnProgress } from "@web/views/view_components/column_progress";
import { isRecordRotting } from "./rotting_widget";

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
        return {
            title: isRottingField.string,
            value: group.list.records.filter(isRecordRotting).length,
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
