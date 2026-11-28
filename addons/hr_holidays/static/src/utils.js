import { user } from "@web/core/user";

export async function userHasEmployeeInCurrentCompany(orm) {
    const [readUser] = await orm
        .cache({ type: "disk", update: "always" })
        .read("res.users", [user.userId], ["employee_id"]);
    return Boolean(readUser.employee_id);
}
