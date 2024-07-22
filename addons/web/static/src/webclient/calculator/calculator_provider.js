import { Component } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { DefaultCommandItem } from "@web/core/commands/command_palette";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { parseFloat } from "@web/views/fields/parsers";
import { formatFloat } from "@web/core/utils/numbers";

const commandCategoryRegistry = registry.category("command_categories");
const commandSetupRegistry = registry.category("command_setup");
const commandProviderRegistry = registry.category("command_provider");

commandCategoryRegistry.add("calculator", { namespace: "=", name: _t("ans") }, { sequence: 120 });

export class Calculator extends Component {
    static template = "web.Calculator";
    static props = {
        ...DefaultCommandItem.props,
    };
}

// -----------------------------------------------------------------------------
// add = namespace + provider
// -----------------------------------------------------------------------------

commandSetupRegistry.add("=", {
    emptyMessage: _t("Enter a valid expression"),
    name: _t("calculator"),
    debounceDelay: 200,
    placeholder: _t("Enter mathematical expression"),
});

commandProviderRegistry.add("=", {
    namespace: "=",
    provide: (env, options = {}) => {
        const commands = [];
        try {
            const result = parseFloat(options.searchValue);
            if(result == "Infinity"){
                throw new Error('Invalid Expression');
            }
            const formattedValue = formatFloat(result);
            const resultString = formattedValue.toString();
            const expressionCommand = {
                Component: Calculator,
                category: "calculator",
                name: resultString,
                action: () => {
                    browser.navigator.clipboard.writeText(formattedValue);
                },
            };
            commands.push(expressionCommand);
        } catch {
            return [];
        }
        return commands;
    },
});
