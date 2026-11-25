import { user } from "@web/core/user";

export async function userHasEmployeeInCurrentCompany(orm) {

    const [readUser] = await orm.read("res.users", [user.userId], ["employee_id"]);
    return Boolean(readUser.employee_id);
}

export async function canRequestAllocation(orm) {
    return orm.call("hr.leave.allocation", "has_requestable_work_entry_type", []);
}
