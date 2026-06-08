import { props, t } from "@odoo/owl";

import { ColumnProgress, columnProgressProps } from "@web/views/view_components/column_progress";

export class RottingColumnProgress extends ColumnProgress {
    static template = "mail.RottingColumnProgress";
    props = props({
        ...columnProgressProps,
        progressBarState: t.object(),
        onRotIconClicked: t.function(),
    });

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
    async onRottingIconClick() {
        await this.props.onRotIconClicked(this.props.group);
    }
}
