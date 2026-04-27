import { registry } from "@web/core/registry";

export const createEditProjectIdsService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        let projectIds;
        return {
            async fetchProjectIds() {
                if (projectIds === undefined) {
                    projectIds = await orm.call(
                        "project.project",
                        "get_create_edit_project_ids",
                        []
                    );
                }
                return projectIds;
            },
            get projectIds() {
                return projectIds;
            },
        };
    },
};

registry.category("services").add("create_edit_project_ids", createEditProjectIdsService);
