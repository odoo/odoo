import { defineModels } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { MailActivityTodoCreate } from "@project_todo/../tests/hoot/mock_server/mock_models/mail_activity_todo_create";

export function defineProjectTodoModels() {
    return defineModels(projectTodoModels);
}

export const projectTodoModels = {
    ...mailModels,
    MailActivityTodoCreate,
};
