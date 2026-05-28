import { animationFrame, describe, expect, queryAllTexts, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
    toggleActionMenu,
    toggleMenuItem,
} from "@web/../tests/web_test_helpers";

// Two separate PropertiesDefinition fields on ResCompany so we can control each
// independently: definitions_a (has 1 prop defined) and definitions_b (empty).
class Partner extends models.Model {
    display_name = fields.Char();
    company_id = fields.Many2one({ string: "Company", relation: "res.company" });
    properties = fields.Properties({
        string: "Properties A",
        searchable: false,
        definition_record: "company_id",
        definition_record_field: "definitions_a",
    });
    properties2 = fields.Properties({
        string: "Properties B",
        searchable: false,
        definition_record: "company_id",
        definition_record_field: "definitions_b",
    });
    _records = [
        {
            id: 1,
            display_name: "Partner With A Prop",
            // A has a value set, B has nothing -> matches definitions_a having 1 def, definitions_b empty
            properties: { prop_a1: "hello" },
            properties2: {},
            company_id: 1,
        },
        {
            id: 2,
            display_name: "Partner No Props",
            properties: {},
            properties2: {},
            company_id: 2,
        },
    ];
}

class ResCompany extends models.Model {
    _name = "res.company";
    name = fields.Char({ string: "Name" });
    definitions_a = fields.PropertiesDefinition();
    definitions_b = fields.PropertiesDefinition();
    _records = [
        {
            id: 1,
            name: "Acme",
            // A has 1 definition, B has none -> lets us test 0-def and ≥1-def in the same record
            definitions_a: [{ name: "prop_a1", string: "Prop A1", type: "char" }],
            definitions_b: [],
        },
        {
            id: 2,
            name: "Empty Co",
            definitions_a: [],
            definitions_b: [],
        },
    ];
}

defineModels([Partner, ResCompany]);

// --- arches ------------------------------------------------------------------

// One properties field only -> original cog menu behavior should be unchanged.
const ARCH_ONE_PROP = /* xml */ `
    <form>
        <sheet>
            <group>
                <field name="company_id"/>
                <field name="properties"/>
            </group>
        </sheet>
    </form>`;

// Two properties fields on the same page -> triggers our multi-def dropdown.
const ARCH_TWO_PROPS = /* xml */ `
    <form>
        <sheet>
            <group>
                <field name="company_id"/>
                <field name="properties"/>
                <field name="properties2"/>
            </group>
        </sheet>
    </form>`;

// Each field lives in a separate notebook tab -> only the active tab is mounted.
const ARCH_NOTEBOOK = /* xml */ `
    <form>
        <sheet>
            <group>
                <field name="company_id"/>
            </group>
            <notebook>
                <page string="Tab A">
                    <field name="properties"/>
                </page>
                <page string="Tab B">
                    <field name="properties2"/>
                </page>
            </notebook>
        </sheet>
    </form>`;

// Mixed: one field always mounted (sheet), one in a tab.
const ARCH_MIXED_PROPS = /* xml */ `
    <form>
        <sheet>
            <field name="company_id"/>
            <field name="properties"/>
            <notebook>
                <page string="Tab A">
                    <div class="tab_a_content">Empty</div>
                </page>
                <page string="Tab B">
                    <field name="properties2"/>
                </page>
            </notebook>
        </sheet>
    </form>`;

// --- helpers -----------------------------------------------------------------

// Opens the nested "Edit Properties" sub-dropdown inside the already-open cog menu.
async function openEditPropertiesSubdropdown() {
    await contains("button.o-dropdown:contains(Edit Properties)").click();
    await animationFrame();
}

// Returns the text of every item in the "Edit Properties" sub-dropdown.
function getSubdropdownItems() {
    return queryAllTexts(".o-dropdown--menu-submenu span.o-dropdown-item");
}

// =============================================================================
// 1. Single properties field -> backward compatibility
// =============================================================================

describe("single properties field", () => {
    test("Edit Properties appears as a plain item, not a nested sub-dropdown", async () => {
        // With only 1 properties field isDisplayed() returns false -> our component is not
        // rendered -> only the original static item (a DropdownItem) is visible.
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_ONE_PROP,
            actionMenus: {},
        });
        await toggleActionMenu();

        // plain DropdownItem with o_menu_item class, not a button.o-dropdown trigger
        expect(".o-dropdown--menu .o_menu_item:contains(Edit Properties)").toHaveCount(1);
        expect("button.o-dropdown:contains(Edit Properties)").toHaveCount(0);
    });

    test("clicking Edit Properties enters edit mode when the user can write on the parent", async () => {
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_ONE_PROP,
            actionMenus: {},
        });
        await toggleActionMenu();
        await toggleMenuItem("Edit Properties");
        await animationFrame();

        // pencil icons (open-definition buttons) are shown next to each property
        expect("[name='properties'] .o_field_property_open_popover").not.toBeEmpty();
    });

    test("clicking Edit Properties shows a warning when user cannot write on the parent", async () => {
        onRpc("has_access", () => false);
        const formView = await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_ONE_PROP,
            actionMenus: {},
        });
        patchWithCleanup(formView.env.services.notification, {
            add: () => expect.step("warning"),
        });

        await toggleActionMenu();
        await toggleMenuItem("Edit Properties");
        await animationFrame();

        expect.verifySteps(["warning"]);
        // not in edit mode -> no edit buttons, no add button
        expect("[name='properties'] .o_field_property_open_popover").toHaveCount(0);
    });

    test("0 definitions: Edit Properties auto-creates a property and opens its popover", async () => {
        // partner 2 -> company 2 -> definitions_a empty -> onPropertyCreate() should fire
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 2,
            arch: ARCH_ONE_PROP,
            actionMenus: {},
        });
        await toggleActionMenu();
        await toggleMenuItem("Edit Properties");
        await animationFrame();

        // a new property was created inline and its definition popover is open
        expect(".o_property_field_popover").toHaveCount(1);
    });

    test("≥1 definitions: Edit Properties enters edit mode without auto-creating a property", async () => {
        // partner 1 -> company 1 -> definitions_a has 1 prop -> no auto-create expected
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_ONE_PROP,
            actionMenus: {},
        });
        await toggleActionMenu();
        await toggleMenuItem("Edit Properties");
        await animationFrame();

        expect(".o_property_field_popover").toHaveCount(0);
        expect("[name='properties'] .o_field_property_open_popover").not.toBeEmpty();
    });
});

// =============================================================================
// 2. Multiple properties fields -> new sub-dropdown behavior
// =============================================================================

describe("multiple properties fields - cog menu rendering", () => {
    test("original static 'Edit Properties' item is hidden when 2 fields are in the arch", async () => {
        // getStaticActionMenuItems() sets addPropertyFieldValue.isAvailable = () => false
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_TWO_PROPS,
            actionMenus: {},
        });
        await toggleActionMenu();

        // the static action item that would normally appear is gone
        expect(".o-dropdown--menu > .o_menu_item:contains(Edit Properties)").toHaveCount(0);
    });

    test("Edit Properties appears as a nested sub-dropdown trigger when 2 fields are mounted", async () => {
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_TWO_PROPS,
            actionMenus: {},
        });
        await toggleActionMenu();

        // a button.o-dropdown (nested Dropdown trigger) is rendered, not a plain DropdownItem
        expect("button.o-dropdown:contains(Edit Properties)").toHaveCount(1);
    });

    test("sub-dropdown lists both fields by their label strings", async () => {
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_TWO_PROPS,
            actionMenus: {},
        });
        await toggleActionMenu();
        await openEditPropertiesSubdropdown();

        expect(getSubdropdownItems()).toEqual(["Properties A", "Properties B"]);
    });
});

describe("multiple properties fields - editing behavior", () => {
    test("selecting field A puts only A in edit mode, B stays untouched", async () => {
        // partner 1 -> A has 1 def (edit buttons visible), B has 0 defs (no buttons to check)
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_TWO_PROPS,
            actionMenus: {},
        });
        await toggleActionMenu();
        await openEditPropertiesSubdropdown();
        await contains(".o-dropdown--menu-submenu .o-dropdown-item:contains(Properties A)").click();
        await animationFrame();

        expect("[name='properties'] .o_field_property_open_popover").not.toBeEmpty();
        // B is not in edit mode -> add button is hidden outside edit mode
        expect("[name='properties2'] .o_field_property_add button").toHaveCount(0);
    });

    test("selecting field B puts only B in edit mode, A stays untouched", async () => {
        // A has 1 def, B has 0 -> B enters edit mode with the add (+) button visible
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_TWO_PROPS,
            actionMenus: {},
        });
        await toggleActionMenu();
        await openEditPropertiesSubdropdown();
        await contains(".o-dropdown--menu-submenu .o-dropdown-item:contains(Properties B)").click();
        await animationFrame();

        expect("[name='properties2'] .o_field_property_add button").toHaveCount(1);
        // A is not in edit mode -> its add button is also hidden
        expect("[name='properties'] .o_field_property_add button").toHaveCount(0);
    });

    test("no write access: selecting a field shows a warning and does not enter edit mode", async () => {
        onRpc("has_access", () => false);
        const formView = await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_TWO_PROPS,
            actionMenus: {},
        });
        patchWithCleanup(formView.env.services.notification, {
            add: () => expect.step("warning"),
        });

        await toggleActionMenu();
        await openEditPropertiesSubdropdown();
        await contains(".o-dropdown--menu-submenu .o-dropdown-item:contains(Properties A)").click();
        await animationFrame();

        expect.verifySteps(["warning"]);
        expect("[name='properties'] .o_field_property_open_popover").toHaveCount(0);
        expect("[name='properties2'] .o_field_property_add button").toHaveCount(0);
    });

    test("selecting A (≥1 defs): enters edit mode without auto-creating a property", async () => {
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_TWO_PROPS,
            actionMenus: {},
        });
        await toggleActionMenu();
        await openEditPropertiesSubdropdown();
        await contains(".o-dropdown--menu-submenu .o-dropdown-item:contains(Properties A)").click();
        await animationFrame();

        expect(".o_property_field_popover").toHaveCount(0);
        expect("[name='properties'] .o_field_property_open_popover").not.toBeEmpty();
    });

    //fix this test
    test("selecting B (0 defs): auto-creates a property and opens its popover", async () => {
        // This exercises the fixed race condition: openPropertyDefinition must be set
        // AFTER await record.update() so the DOM is ready when useEffect fires.
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_MIXED_PROPS,
            actionMenus: {},
        });

        // Initially only A is in the cog menu because B is in inactive Tab B
        await toggleActionMenu();
        expect(".o_menu_item:contains(Edit Properties)").toHaveCount(1);
        expect("button.o-dropdown:contains(Edit Properties)").toHaveCount(0);
        await toggleActionMenu(); // close

        // Switch to Tab B to mount properties2 (field B has 0 defs in record 1)
        await contains(".o_notebook .nav-link:contains(Tab B)").click();
        await animationFrame();

        await toggleActionMenu();
        await openEditPropertiesSubdropdown();
        await contains(".o-dropdown--menu-submenu .o_menu_item:contains(Properties B)").click();
        await animationFrame();

        expect(".o_property_field_popover").toHaveCount(1);
    });

    test("both fields in 0-def company: selecting either auto-creates a property", async () => {
        // partner 2 -> company 2 -> both definitions empty
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 2,
            arch: ARCH_TWO_PROPS,
            actionMenus: {},
        });
        await toggleActionMenu();
        await openEditPropertiesSubdropdown();
        await contains(".o-dropdown--menu-submenu .o-dropdown-item:contains(Properties A)").click();
        await animationFrame();

        expect(".o_property_field_popover").toHaveCount(1);
    });
});

// =============================================================================
// 3. Notebook tab behavior -> mount/unmount lifecycle
// =============================================================================

describe("notebook tabs", () => {
    test("initial state: only the active tab's field appears in the cog menu", async () => {
        // Tab A is active by default -> only 'properties' is mounted -> only 1 field mounted.
        // Template branch: propertiesFields.length === 1 -> DropdownItem.
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_NOTEBOOK,
            actionMenus: {},
        });
        await toggleActionMenu();

        expect("button.o-dropdown:contains(Edit Properties)").toHaveCount(0);
        expect(".o_menu_item:contains(Edit Properties)").toHaveCount(1);
    });

    test("after switching to Tab B: Properties B replaces Properties A (still a plain item)", async () => {
        // OWL destroys Tab A content when Tab B becomes active -> onWillUnmount removes A,
        // onMounted adds B -> reactive registry updates -> component re-renders.
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_NOTEBOOK,
            actionMenus: {},
        });
        await contains(".o_notebook .nav-link:eq(1)").click();
        await animationFrame();

        await toggleActionMenu();

        // Still only 1 field mounted (B), so still a plain item
        expect("button.o-dropdown:contains(Edit Properties)").toHaveCount(0);
        expect(".o_menu_item:contains(Edit Properties)").toHaveCount(1);
    });

    test("with 1 field mounted: component renders as a plain DropdownItem, not a sub-dropdown", async () => {
        // isDisplayed() -> true (2 fields in root.fields), but only 1 is mounted (Tab A active).
        // Template branch: propertiesFields.length === 1 -> DropdownItem with o_menu_item class.
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_NOTEBOOK,
            actionMenus: {},
        });
        await toggleActionMenu();

        expect("button.o-dropdown:contains(Edit Properties)").toHaveCount(0);
        expect(".o_menu_item:contains(Edit Properties)").toHaveCount(1);
    });

    test("clicking the plain item (1 field mounted) puts that field in edit mode", async () => {
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_NOTEBOOK,
            actionMenus: {},
        });
        await toggleActionMenu();
        await toggleMenuItem("Edit Properties");
        await animationFrame();

        // Tab A active -> 'properties' entered edit mode
        expect("[name='properties'] .o_field_property_open_popover").not.toBeEmpty();
    });

    test("clicking plain item on Tab B puts properties2 in edit mode", async () => {
        // Switch to Tab B first -> properties2 mounts, properties unmounts -> component has 1 entry.
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_NOTEBOOK,
            actionMenus: {},
        });
        await contains(".o_notebook .nav-link:eq(1)").click();
        await animationFrame();

        await toggleActionMenu();
        await toggleMenuItem("Edit Properties");
        await animationFrame();

        // B is in edit mode (0 defs -> add button visible)
        expect("[name='properties2'] .o_field_property_add button").toHaveCount(1);
    });

    test("tab switch removes the previous field from the mounted registry", async () => {
        // After switching away from Tab A, 'properties' must no longer be in the dropdown.
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_NOTEBOOK,
            actionMenus: {},
        });

        await contains(".o_notebook .nav-link:eq(1)").click();
        await animationFrame();
        await toggleActionMenu();
        // with only B mounted the component renders as DropdownItem, not a sub-dropdown
        expect("button.o-dropdown:contains(Edit Properties)").toHaveCount(0);

        await toggleMenuItem("Edit Properties");
        await animationFrame();

        // A is not visible (it's on the inactive tab) and definitely not in edit mode
        expect("[name='properties']").toHaveCount(0);
    });
});

// =============================================================================
// 4. Edge cases
// =============================================================================

describe("edge cases", () => {
    test("no properties field in the arch: Edit Properties item does not appear at all", async () => {
        // Regression guard: form with no properties field -> no cog menu item of any kind.
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: /* xml */ `<form><sheet><field name="display_name"/></sheet></form>`,
            actionMenus: {},
        });
        await toggleActionMenu();

        expect(".o-dropdown--menu span:contains(Edit Properties)").toHaveCount(0);
        expect("button.o-dropdown:contains(Edit Properties)").toHaveCount(0);
    });

    test("readonly form: Edit Properties item is absent (field is readonly -> handler exits early)", async () => {
        // The properties field returns early from the bus handler when props.readonly is true.
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: /* xml */ `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties" readonly="1"/>
                            <field name="properties2" readonly="1"/>
                        </group>
                    </sheet>
                </form>`,
            actionMenus: {},
        });
        await toggleActionMenu();
        await openEditPropertiesSubdropdown();

        // Verify selecting either field does nothing (no edit mode entered)
        await contains(".o-dropdown--menu-submenu .o-dropdown-item:contains(Properties A)").click();
        await animationFrame();

        expect("[name='properties'] .o_field_property_open_popover").toHaveCount(0);
    });

    test("already in edit mode: triggering the event again is a no-op", async () => {
        // The handler returns early if isInEditMode is already true -> prevents double-edit.
        onRpc("has_access", () => true);
        await mountView({
            type: "form",
            resModel: "partner",
            resId: 1,
            arch: ARCH_TWO_PROPS,
            actionMenus: {},
        });

        // First click -> enters edit mode
        await toggleActionMenu();
        await openEditPropertiesSubdropdown();
        await contains(".o-dropdown--menu-submenu .o-dropdown-item:contains(Properties A)").click();
        await animationFrame();
        expect("[name='properties'] .o_field_property_open_popover").not.toBeEmpty();

        // Second click on the same field -> should still show exactly 1 popover (not a second)
        await toggleActionMenu();
        await openEditPropertiesSubdropdown();
        await contains(".o-dropdown--menu-submenu .o-dropdown-item:contains(Properties A)").click();
        await animationFrame();
        expect(".o_property_field_popover").toHaveCount(0);
    });
});
