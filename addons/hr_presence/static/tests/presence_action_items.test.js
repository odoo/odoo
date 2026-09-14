import { describe, expect, test } from "@odoo/hoot";
import { COG_GROUP } from "@web/search/cog_menu/cog_menu_group";
import {
    groupPresenceActionItems,
    withPresenceSubMenu,
} from "@hr_presence/views/presence_action_items";

describe.current.tags("headless");

const boundAction = (name, section, sequence) => ({
    key: name,
    description: name,
    groupNumber: COG_GROUP.ACTIONS,
    action: {
        id: name,
        name,
        binding_sequence: sequence,
        hr_presence_section: section,
    },
});

const foreignAction = (name, sequence) => ({
    key: name,
    description: name,
    groupNumber: COG_GROUP.ACTIONS,
    action: { id: name, name, binding_sequence: sequence },
});

const staticItem = (name) => ({
    key: name,
    description: name,
    groupNumber: COG_GROUP.DANGER,
});

const submenuOf = (items) => items.find((item) => item.key === "hr_presence_control");

test("the presence actions are collapsed into one submenu", () => {
    const grouped = groupPresenceActionItems(
        [
            boundAction("Set Present", "state", 10),
            boundAction("Add a Log Note", "follow_up", 20),
            staticItem("Delete"),
        ],
        () => {},
    );
    const submenu = submenuOf(grouped);
    expect(submenu).not.toBe(undefined, { message: "a submenu is produced" });
    expect(submenu.props.items.map((item) => item.description)).toEqual([
        "Set Present",
        "Add a Log Note",
    ]);
    expect(grouped.map((item) => item.key)).toEqual(["hr_presence_control", "Delete"]);
});

test("an action another module bound to the same model is left alone", () => {
    // binding_sequence defaults to 10, so hr's Create User and hr_skills' Resume
    // both sit in the band this once inferred the section from. Only the field
    // says whether an action is ours.
    const grouped = groupPresenceActionItems(
        [
            boundAction("Set Present", "state", 10),
            foreignAction("Create User", 10),
            foreignAction("Resume", 10),
        ],
        () => {},
    );
    expect(submenuOf(grouped).props.items.map((item) => item.description)).toEqual([
        "Set Present",
    ]);
    expect(grouped.map((item) => item.key)).toInclude("Create User");
    expect(grouped.map((item) => item.key)).toInclude("Resume");
});

test("the section decides the group the divider is drawn between", () => {
    const submenu = submenuOf(
        groupPresenceActionItems(
            [
                boundAction("Add a Log Note", "follow_up", 20),
                boundAction("Set Present", "state", 10),
            ],
            () => {},
        ),
    );
    const byName = Object.fromEntries(
        submenu.props.items.map((item) => [item.description, item.groupNumber]),
    );
    expect(byName["Set Present"]).toBe(0);
    expect(byName["Add a Log Note"]).toBe(1);
    expect(byName["Set Present"]).toBeLessThan(byName["Add a Log Note"]);
});

test("an unknown section name is not ours either", () => {
    const grouped = groupPresenceActionItems(
        [boundAction("Something Else", "made_up", 10)],
        () => {},
    );
    expect(submenuOf(grouped)).toBe(undefined);
    expect(grouped.map((item) => item.key)).toEqual(["Something Else"]);
});

test("with no presence action there is no empty submenu", () => {
    const items = [foreignAction("Create User", 10), staticItem("Delete")];
    expect(groupPresenceActionItems(items, () => {})).toEqual(items);
});

test("a static item with no action at all is untouched", () => {
    const grouped = groupPresenceActionItems(
        [staticItem("Export"), boundAction("Set Absent", "state", 11)],
        () => {},
    );
    expect(grouped.map((item) => item.key)).toInclude("Export");
    expect(submenuOf(grouped).props.items).toHaveLength(1);
});

test("the submenu carries the caller's selection handler", () => {
    const picked = [];
    const submenu = submenuOf(
        groupPresenceActionItems([boundAction("Send SMS…", "follow_up", 22)], (item) =>
            picked.push(item.description),
        ),
    );
    submenu.props.onItemSelected(submenu.props.items[0]);
    expect(picked).toEqual(["Send SMS…"]);
});

test("withPresenceSubMenu extends the class it is given, it does not replace it", async () => {
    class Base {
        constructor() {
            this.seen = [];
        }
        async getActionItems() {
            return [boundAction("Set Present", "state", 10), staticItem("Delete")];
        }
        onItemSelected(item) {
            this.seen.push(item);
        }
    }
    const Extended = withPresenceSubMenu(Base);
    expect(Extended.prototype instanceof Base).toBe(true);
    const grouped = await new Extended().getActionItems({});
    expect(submenuOf(grouped)).not.toBe(undefined);
});
