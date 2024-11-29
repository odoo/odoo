import { defineModels } from "@web/../tests/web_test_helpers";

import { mailModels } from "@mail/../tests/mail_test_helpers";
import { projectModels } from "@project/../tests/project_models";

import { ProjectTask } from "./mock_server/mock_models/project_task";
import { ProjectTags } from "./mock_server/mock_models/project_tags";
import { MailActivityTodoCreate } from "./mock_server/mock_models/mail_activity_todo_create";

export function defineTodoModels() {
    defineModels(todoodoModels);
}

export const todoodoModels = {
    ...mailModels,
    ...projectModels,
    ProjectTask,
    ProjectTags,
    MailActivityTodoCreate,
};
