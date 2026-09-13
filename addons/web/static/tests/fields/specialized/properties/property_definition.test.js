// @ts-check
import { afterEach, beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { EventBus } from "@odoo/owl";
import {
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { enableLogging, getStatus, makeLogger } from "@web/core/debug/debug_logger";
import { PropertyDefinition } from "@web/fields/specialized/properties/property_definition";

const log = makeLogger("web.field.property_definition");
let previousLogSpec;
beforeEach(() => {
    previousLogSpec = getStatus().spec;
    enableLogging("web.field.*", { persist: false });
});
afterEach(() => enableLogging(previousLogSpec, { persist: false }));
class Item extends models.Model {
    name = fields.Char();
    _records = [
        { id: 1, name: "One" },
        { id: 2, name: "Two" },
    ];
}
defineModels([Item]);

function mountDefinition() {
    return mountWithCleanup(PropertyDefinition, {
        props: {
            fieldName: "properties",
            propertyIndex: 0,
            propertiesSize: 1,
            context: {},
            readonly: true,
            record: { fields: {}, model: { bus: new EventBus() } },
            propertyDefinition: {
                name: "property",
                string: "Property",
                type: "many2one",
                comodel: "item",
                domain: "[]",
                default: false,
            },
            onChange: () => {},
        },
    });
}

test("clearing a property's model invalidates its pending description", async () => {
    const pending = new Deferred();
    onRpc("ir.model", "display_name_for", () => pending);
    const component = await mountDefinition();
    await component._syncStateWithProps({
        ...component.state.propertyDefinition,
        comodel: "",
    });
    pending.resolve([{ display_name: "Old Model" }]);
    await animationFrame();
    log.logic("description after clearing", {
        description: component.state.resModelDescription,
    });
    expect(component.state.resModelDescription).toBe("");
    expect(".o_field_property_definition").not.toHaveText(/Old Model/);
});

test("clearing a property's model invalidates its pending count", async () => {
    onRpc("ir.model", "display_name_for", () => [{ display_name: "Item" }]);
    const pending = new Deferred();
    onRpc("item", "search_count", () => pending);
    const component = await mountDefinition();
    await animationFrame();
    await component._syncStateWithProps({
        ...component.state.propertyDefinition,
        comodel: "",
    });
    pending.resolve(42);
    await animationFrame();
    log.logic("count after clearing", { count: component.state.matchingRecordsCount });
    expect(component.state.matchingRecordsCount).toBe(undefined);
});

test("a replacement property domain refreshes the count on the same model", async () => {
    onRpc("ir.model", "display_name_for", () => [{ display_name: "Item" }]);
    const component = await mountDefinition();
    await animationFrame();
    expect(component.state.matchingRecordsCount).toBe(2);
    await component._syncStateWithProps({
        ...component.state.propertyDefinition,
        domain: "[('id', '=', 1)]",
    });
    await animationFrame();
    log.logic("count after new domain", {
        count: component.state.matchingRecordsCount,
    });
    expect(component.state.matchingRecordsCount).toBe(1);
    expect(".o_field_property_definition_domain button").toHaveText("1 record(s)");
});

test("invalid property domains cancel pending counts without throwing", async () => {
    onRpc("ir.model", "display_name_for", () => [{ display_name: "Item" }]);
    const pending = new Deferred();
    onRpc("item", "search_count", () => pending);
    const component = await mountDefinition();
    await animationFrame();
    await component.onDomainChange("not a domain");
    pending.resolve(42);
    await animationFrame();
    log.logic("count after invalid domain", {
        count: component.state.matchingRecordsCount,
    });
    expect(component.state.matchingRecordsCount).toBe(undefined);
});

test("changing a relational property to text cancels pending metadata", async () => {
    const pending = new Deferred();
    onRpc("ir.model", "display_name_for", () => pending);
    const component = await mountDefinition();
    component.onPropertyTypeChange("char");
    pending.resolve([{ display_name: "Old Model" }]);
    await animationFrame();
    log.logic("metadata after type change", {
        model: component.state.resModel,
        description: component.state.resModelDescription,
    });
    expect(component.state.resModel).toBe("");
    expect(component.state.resModelDescription).toBe("");
    expect(component.state.matchingRecordsCount).toBe(undefined);
});
