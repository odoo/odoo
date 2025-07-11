import { ColumnProgress } from "@web/views/view_components/column_progress";

export class RottingColumnProgress extends ColumnProgress {
    static template = "mail.RottingColumnProgress";
    static props = {
        ...ColumnProgress.props,
        progressBarState: { type: Object },
        onRotIconClicked: { type: Function },
    };

    getRottingGroupCount(group) {
        const rotField = this.props.progressBarState.progressAttributes.rotting_count_field;
        const rotCount = { title: rotField.string, value: 0 };
        group.list.records.forEach((record) => {
            if (record.data[rotField.name]) {
                rotCount.value++;
            }
        });
        return rotCount;
    }

    async onRotIconClick() {
        await this.props.onRotIconClicked();
    }
}
