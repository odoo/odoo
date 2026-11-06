import { expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { queryAllTexts } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { openReport } from "./utils";

definePosModels();

test("loads report with session defaults", async () => {
    const report = await openReport(1, { default_filters: { session_id: 1 } });
    expect(report.options().session_id).toBe(1);
    expect(".o_breadcrumb").toHaveText("Sales Details");
    expect(queryAllTexts(".o_report_column_header")).toEqual(["Qty", "Total"]);
    expect(queryAllTexts(".line_level_0 .o_report_cell")).toEqual(["2", "$ 18.00"]);
});

test("unfolds and folds annotated products", async () => {
    await openReport();

    await contains(".line_level_1 .o_report_name_cell").click();

    expect(".line_level_1").toHaveClass("o_report_unfolded");
    expect(".line_level_2").toHaveCount(2);
    expect(queryAllTexts(".line_level_2 .o_report_cell")).toEqual(["1", "$ 9.00", "1", "$ 9.00"]);
    expect(queryAllTexts(".line_level_2:contains('Coffee') small")).toEqual([
        "(Milk, Sugar)",
        "kg",
        "Disc: 10%",
    ]);

    await contains(".line_level_1 .o_report_name_cell").click();
    expect(".line_level_1").not.toHaveClass("o_report_unfolded");
    expect(".line_level_2").toHaveCount(0);
});

test("toggles Unfold All", async () => {
    const report = await openReport();

    await contains("button:contains('Options')").click();
    await contains(".dropdown-item:contains('Unfold All')").click();

    expect(report.options().unfold_all).toBe(true);
    expect(".line_level_0").toHaveClass("o_report_unfolded");
    expect(".line_level_1").toHaveClass("o_report_unfolded");
    expect(".line_level_2 .o_report_toggle_empty").toHaveCount(2);

    await contains("button:contains('Options')").click();
    await contains(".dropdown-item:contains('Unfold All')").click();

    expect(report.options().unfold_all).toBe(false);
    expect(".line_level_1").not.toHaveClass("o_report_unfolded");
    expect(".line_level_2").toHaveCount(0);
});

test("filters report and preserves folds", async () => {
    mockDate("2026-01-01 12:00:00", 0);
    const report = await openReport();
    await contains(".line_level_0 .o_report_name_cell").click();
    await contains("button:contains('Point of Sale')").click();
    await contains(".pos_report_filter.multiselect input").click();
    await contains(".o-autocomplete--dropdown-item:contains('Hoot')").click();
    await contains("button:contains('Session')").click();
    await contains(".pos_report_filter.singleselect input").click();
    await contains(".o-autocomplete--dropdown-item:contains('/')").click();
    expect(report.options()).toEqual({
        date_from: "2026-01-01 00:00:00",
        date_to: "2026-01-31 23:59:59",
        config_ids: [1],
        session_id: 1,
    });
    expect(".line_level_0").not.toHaveClass("o_report_unfolded");
    expect(".line_level_1").toHaveCount(0);
});

test("updates the session domain when the config changes", async () => {
    const report = await openReport(1, { default_filters: { config_ids: [1], session_id: 1 } });
    const sessionFilter = report.meta().filters.find((filter) => filter.key === "session_id");
    const staticDomain = [["state", "=", "opened"]];
    const filter = { ...sessionFilter, domain: [...staticDomain, ...sessionFilter.domain] };

    expect(report.getFilterDomain(filter)).toEqual([...staticDomain, ["config_id", "in", [1]]]);

    await report.applyFilters({ config_ids: [2] });
    expect(report.getFilterDomain(filter)).toEqual([...staticDomain, ["config_id", "in", [2]]]);
    expect(report.options().session_id).toBe(false);

    await report.applyFilters({ config_ids: [] });
    expect(report.getFilterDomain(filter)).toEqual(staticDomain);
});

test("restores report options when reopening the report", async () => {
    mockDate("2026-01-01 12:00:00", 0);
    const report = await openReport();
    const date_to = "2026-12-31 23:59:59";
    await report.applyFilters({ date_to, config_ids: [1] });
    await report.unfoldAll();

    const reopened = await openReport();
    expect(reopened.options()).toMatchObject({ date_to, config_ids: [1], unfold_all: true });
    const category = reopened.sections[0].lines[0];
    expect(category.foldability).toBe("expanded");

    reopened.toggleUnfold(category);
    const folded = await openReport();
    expect(folded.options().unfold_all).toBe(false);
    expect(folded.sections[0].lines[0].foldability).toBe("collapsed");
});

test("action defaults override saved report options", async () => {
    const report = await openReport();
    await report.applyFilters({ session_id: 1, config_ids: [1] });

    const reopened = await openReport(1, { default_filters: { session_id: false } });
    expect(reopened.options()).toMatchObject({ session_id: false, config_ids: [1] });
});

test("ignore_session bypasses saved report options", async () => {
    const report = await openReport();
    await report.applyFilters({ config_ids: [1] });
    await report.unfoldAll();

    const reopened = await openReport(1, {}, { ignore_session: true });
    expect(reopened.options().config_ids).toEqual([]);
    expect(reopened.sections[0].lines[0].foldability).toBe("collapsed");
});
