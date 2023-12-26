/** @odoo-module **/

import { useCommand } from "@web/core/commands/command_hook";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";

const { useComponent, useEnv } = owl;

/**
 * Use this hook to add "Assign to.." and "Assign/Unassign me" to the command palette.
 */

export function useAssignUserCommand() {
    const component = useComponent();
    const env = useEnv();
    const orm = useService("orm");
    const user = useService("user");
    if (
        component.props.relation !== "res.users" ||
        component.props.record.activeFields[component.props.name].viewType !== "form"
    ) {
        return;
    }

    const getCurrentIds = () => {
        if (component.props.type === "many2one" && component.props.value) {
            return [component.props.value[0]];
        } else if (component.props.type === "many2many") {
            return component.props.value.currentIds;
        }
        return [];
    };

    const add = async (record) => {
        if (component.props.type === "many2one") {
            component.props.update(record);
        } else if (component.props.type === "many2many") {
            component.props.update({
                operation: "REPLACE_WITH",
                resIds: [...getCurrentIds(), record[0]],
            });
        }
    };

    const remove = async (record) => {
        if (component.props.type === "many2one") {
            component.props.update([]);
        } else if (component.props.type === "many2many") {
            component.props.update({
                operation: "REPLACE_WITH",
                resIds: getCurrentIds().filter((id) => id !== record[0]),
            });
        }
    };

    const provide = async (env, options) => {
        const value = options.searchValue.trim();
        let domain = component.props.record.getFieldDomain(component.props.name);
        const context = component.props.record.getFieldContext(component.props.name);
        if (component.props.type === "many2many") {
            const selectedUserIds = getCurrentIds();
            if (selectedUserIds.length) {
                domain = Domain.and([domain, [["id", "not in", selectedUserIds]]]);
            }
        }
        if (component._pendingRpc) {
            component._pendingRpc.abort(false);
        }
        component._pendingRpc = orm.call(component.props.relation, "name_search", [], {
            name: value,
            args: domain.toList(),
            operator: "ilike",
            limit: 80,
            context,
        });
        const searchResult = await component._pendingRpc;
        component._pendingRpc = null;
        return searchResult.map((record) => ({
            name: record[1],
            action: add.bind(null, record),
        }));
    };

    useCommand(
        env._t("Assign to ..."),
        () => ({
            configByNameSpace: {
                default: {
                    emptyMessage: env._t("No users found"),
                },
            },
            placeholder: env._t("Select a user..."),
            providers: [
                {
                    provide,
                },
            ],
        }),
        {
            category: "smart_action",
            hotkey: "alt+i",
            global: true,
        }
    );

    useCommand(
        env._t("Assign/Unassign to me"),
        () => {
            const record = [user.userId, user.name];
            if (getCurrentIds().includes(user.userId)) {
                remove(record);
            } else {
                add(record);
            }
        },
        {
            category: "smart_action",
            hotkey: "alt+shift+i",
            global: true,
        }
    );
}
