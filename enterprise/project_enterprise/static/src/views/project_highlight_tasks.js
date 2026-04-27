import { useService } from "@web/core/utils/hooks";

export function useProjectModelActions({ getContext, getHighlightPlannedIds }) {
    const orm = useService("orm");
    return {
        async getHighlightIds() {
            const context = getContext();
            if (!context || (!context.highlight_conflicting_task && !context.highlight_planned)) {
                return;
            }

            if (context.highlight_conflicting_task) {
                const highlightConflictingIds = await orm.search("project.task", [
                    ["planning_overlap", "!=", false],
                ]);

                if (context.highlight_planned) {
                    return Array.from(
                        new Set([...highlightConflictingIds, ...getHighlightPlannedIds()])
                    );
                }
                return highlightConflictingIds;
            }
            return getHighlightPlannedIds() || [];
        },
    };
}
