import { ResourceTask } from "./mock_server/mock_models/resource_task";
import { ResourceResource } from "./mock_server/mock_models/resource_resource";
import { ResourceCalendar } from "./mock_server/mock_models/resource_calendar";
import { ResourceCalendarAttendance } from "./mock_server/mock_models/resource_calendar_attendance";
import { defineModels } from "@web/../tests/web_test_helpers";

export const resourceModels = {
    ResourceTask,
    ResourceResource,
    ResourceCalendar,
    ResourceCalendarAttendance,
};

export function defineResourceModels() {
    return defineModels(resourceModels);
}
