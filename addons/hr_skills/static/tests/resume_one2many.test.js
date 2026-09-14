import {
    defineHrSkillModels,
    hrSkillModels,
} from "@hr_skills/../tests/hr_skills_test_helpers";
import { contains } from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountView, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineHrSkillModels();

const RESUME_ARCH = `
    <form>
        <field mode="list" nolabel="1" name="resume_line_ids" widget="resume_one2many">
            <list>
                <field name="line_type_id"/>
                <field name="name"/>
                <field name="date_start"/>
                <field name="date_end"/>
            </list>
        </field>
    </form>`;

const RESUME_ARCH_WITH_DESCRIPTION = RESUME_ARCH.replace(
    '<field name="name"/>',
    '<field name="name"/><field name="description"/><field name="is_course"/><field name="external_url"/>',
);

function defineEmployeeWithLine(line) {
    const { HrEmployee, HrResumeLine, HrResumeLineType } = hrSkillModels;
    const typeId = HrResumeLineType._records.length + 1;
    HrResumeLineType._records.push({ id: typeId, name: "Experience" });
    const lineId = HrResumeLine._records.length + 1;
    HrResumeLine._records.push({
        id: lineId,
        line_type_id: typeId,
        date_start: "2020-01-01",
        date_end: "2021-01-01",
        ...line,
    });
    const employeeId = HrEmployee._records.length + 1;
    HrEmployee._records.push({
        id: employeeId,
        name: "Jony McHallyFace",
        resume_line_ids: [lineId],
    });
    onRpc("hr.employee", "get_internal_resume_lines", () => []);
    return employeeId;
}

test("resume_one2many renders a stored line", async () => {
    const employeeId = defineEmployeeWithLine({ name: "Mamie Rock" });

    await mountView({
        type: "form",
        resModel: "hr.employee",
        resId: employeeId,
        arch: RESUME_ARCH,
    });

    await contains(".o_field_resume_one2many");
    expect(".o_resume_line_title").toHaveCount(1);
    expect(".o_resume_line_title").toHaveText("Mamie Rock");
    expect(".o_resume_line_dates").toHaveCount(1);
});

test("a link in a resume line opens in a new tab without opening the line", async () => {
    const employeeId = defineEmployeeWithLine({
        name: "Mamie Rock",
        is_course: true,
        external_url: "https://example.com/course",
        description:
            '<p>See <a href="https://example.com/cert">the certificate</a></p>',
    });

    await mountView({
        type: "form",
        resModel: "hr.employee",
        resId: employeeId,
        arch: RESUME_ARCH_WITH_DESCRIPTION,
    });

    for (const link of [".o_resume_line_desc a", "#external_link"]) {
        await contains(link);
        queryOne(link).addEventListener("click", (ev) => ev.preventDefault());
        await click(link);
        await animationFrame();

        expect(link).toHaveAttribute("target", "_blank");
        expect(link).toHaveAttribute("rel", "noopener noreferrer");
        expect(".modal").toHaveCount(0);
    }

    await click(".o_resume_line_title");
    await animationFrame();
    expect(".modal").toHaveCount(1);
});
