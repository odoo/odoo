/** @odoo-module */

import { getFixture, patchDate, click, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { localization } from "@web/core/l10n/localization";
import { SELECTORS, getGridContent } from "@web_gantt/../tests/helpers";

let serverData;
/** @type {HTMLElement} */
let target;
QUnit.module("Views > AttendanceGanttView", {
    beforeEach() {
        patchDate(2018, 11, 20, 8, 0, 0);

        setupViewRegistries();
        patchWithCleanup(localization, { timeFormat: "hh:mm:ss" });

        target = getFixture();
        serverData = {
            models: {
                users: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 1, name: "User 1" },
                        { id: 2, name: "User 2" },
                    ],
                },
                attendances: {
                    fields: {
                      id: { string: "ID", type: "integer" },
                      check_in: { string: "Start Date", type: "datetime" },
                      check_out: { string: "Stop Date", type: "datetime" },
                      user_id: {
                        string: "Attendance Of",
                        type: "many2one",
                        relation: "users",
                      },
                      name: { string: "Name", type: "String" },
                    },
                    records: [
                      {
                        id: 1,
                        check_in: "2018-12-10 09:00:00",
                        check_out: "2018-12-10 12:00:00",
                        name: "Attendance 1",
                        user_id: 1,
                      },
                      {
                        id: 2,
                        check_in: "2018-12-10 13:00:00",
                        check_out: false,
                        name: "Attendance 2",
                        user_id: 1,
                      },
                      {
                        id: 3,
                        check_in: "2018-12-10 08:00:00",
                        check_out: "2018-12-10 16:00:00",
                        name: "Attendance 3",
                        user_id: 2,
                      },
                    ],
                },
            },
        };
    },
});

QUnit.test("Open Ended record today", async (assert) => {
  patchDate(2018, 11, 10, 17, 0, 0);
  await makeView({
    type: "gantt",
    resModel: "attendances",
    serverData,
    arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
  });
  const { range, rows } = getGridContent();
  assert.strictEqual(range, "Monday, December 10, 2018");
  assert.deepEqual(rows, [
    {
      pills: [
        {
          colSpan: "10am -> 12pm",
          level: 0,
          title: "Attendance 1",
        },
        {
          colSpan: "2pm -> 5pm",
          level: 0,
          title: "Attendance 2",
        },
      ],
      title: "User 1",
    },
    {
      pills: [
        {
          colSpan: "9am -> 4pm",
          level: 0,
          title: "Attendance 3",
        },
      ],
      title: "User 2",
    },
  ]);
});

QUnit.test("Future Open Ended record not displayed", async (assert) => {
  patchDate(2018, 11, 10, 13, 0, 0);
  await makeView({
    type: "gantt",
    resModel: "attendances",
    serverData,
    arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
  });
  const { range, rows } = getGridContent();
  assert.strictEqual(range, "Monday, December 10, 2018");
  assert.deepEqual(rows, [
    {
      pills: [
        {
          colSpan: "10am -> 12pm",
          level: 0,
          title: "Attendance 1",
        },
      ],
      title: "User 1",
    },
    {
      pills: [
        {
          colSpan: "9am -> 4pm",
          level: 0,
          title: "Attendance 3",
        },
      ],
      title: "User 2",
    },
  ]);
});

QUnit.test("Open Ended record spanning multiple days", async (assert) => {
  patchDate(2018, 11, 12, 15, 0, 0);
  await makeView({
    type: "gantt",
    resModel: "attendances",
    serverData,
    arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
  });
  let gridContent = getGridContent()
  assert.strictEqual(gridContent.range, "Wednesday, December 12, 2018");
  assert.deepEqual(gridContent.rows, [
    {
      pills: [
        {
          colSpan: "12am -> 3pm",
          level: 0,
          title: "Attendance 2",
        },
      ],
      title: "User 1",
    },
  ]);
  await click(target, SELECTORS.prevButton);
  gridContent = getGridContent()
  assert.strictEqual(gridContent.range, "Tuesday, December 11, 2018");
  assert.deepEqual(gridContent.rows, [
    {
      pills: [
        {
          colSpan: "12am -> 11pm",
          level: 0,
          title: "Attendance 2",
        },
      ],
      title: "User 1",
    },
  ]);
  await click(target, SELECTORS.prevButton);
  gridContent = getGridContent()
  assert.strictEqual(gridContent.range, "Monday, December 10, 2018");
  assert.deepEqual(gridContent.rows, [
    {
      pills: [
        {
          colSpan: "10am -> 12pm",
          level: 0,
          title: "Attendance 1",
        },
        {
          colSpan: "2pm -> 11pm",
          level: 0,
          title: "Attendance 2",
        },
      ],
      title: "User 1",
    },
    {
      pills: [
        {
          colSpan: "9am -> 4pm",
          level: 0,
          title: "Attendance 3",
        },
      ],
      title: "User 2",
    },
  ]);
});

QUnit.test("Concurrent open-ended records", async (assert) => {
  patchDate(2018, 11, 20, 16, 0, 0);
  serverData.models.attendances.records = [
    {
      id: 4,
      check_in: "2018-12-20 08:00:00",
      check_out: false,
      name: "Attendance 4",
      user_id: 1,
    },
    {
      id: 5,
      check_in: "2018-12-20 09:00:00",
      check_out: false,
      name: "Attendance 5",
      user_id: 1,
    },
  ];

  await makeView({
    type: "gantt",
    resModel: "attendances",
    serverData,
    arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
  });
  const { range, rows } = getGridContent();
  assert.strictEqual(range, "Thursday, December 20, 2018");
  assert.deepEqual(rows, [
    {
      pills: [
        {
          colSpan: "9am -> 4pm",
          level: 0,
          title: "Attendance 4",
        },
        {
          colSpan: "10am -> 4pm",
          level: 1,
          title: "Attendance 5",
        },
      ],
      title: "User 1",
    },
  ]);
});

QUnit.test("Open ended record Precision", async (assert) => {
  patchDate(2018, 11, 20, 16, 35, 0);
  serverData.models.attendances.records = [
    {
      id: 4,
      check_in: "2018-12-20 08:00:00",
      check_out: false,
      name: "Attendance 4",
      user_id: 1,
    },
  ];

  await makeView({
    type: "gantt",
    resModel: "attendances",
    serverData,
    arch: `<gantt js_class="attendance_gantt" date_start="check_in" precision="{'day': 'hour:quarter'}" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
  });
  const { range, rows } = getGridContent();
  assert.strictEqual(range, "Thursday, December 20, 2018");
  assert.deepEqual(rows, [
    {
      pills: [
        {
          colSpan: "9am -> 4pm (3/4)",
          level: 0,
          title: "Attendance 4",
        },
      ],
      title: "User 1",
    },
  ]);
});

QUnit.test("Open ended record updated correctly", async (assert) => {
  patchDate(2018, 11, 20, 15, 0, 0);
  serverData.models.attendances.records = [
    {
      id: 4,
      check_in: "2018-12-20 08:00:00",
      check_out: false,
      name: "Attendance 4",
      user_id: 1,
    },
  ];

  await makeView({
    type: "gantt",
    resModel: "attendances",
    serverData,
    arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
  });
  let gridContent = getGridContent()
  assert.strictEqual(gridContent.range, "Thursday, December 20, 2018");
  assert.deepEqual(gridContent.rows, [
    {
      pills: [
        {
          colSpan: "9am -> 3pm",
          level: 0,
          title: "Attendance 4",
        },
      ],
      title: "User 1",
    },
  ]);
  patchDate(2018, 11, 20, 19, 0, 0);
  await click(target, SELECTORS.nextButton);
  await click(target, SELECTORS.prevButton);
  gridContent = getGridContent()
  assert.strictEqual(gridContent.range, "Thursday, December 20, 2018");
  assert.deepEqual(gridContent.rows, [
    {
      pills: [
        {
          colSpan: "9am -> 7pm",
          level: 0,
          title: "Attendance 4",
        },
      ],
      title: "User 1",
    },
  ]);
});

QUnit.test(
  "Future Open ended record not shown before it happens and appears after start date.",
  async (assert) => {
    patchDate(2018, 10, 2, 13, 0, 0);
    serverData.models.attendances.records = [
      {
        id: 5,
        check_in: "2018-11-02 09:00:00",
        check_out: "2018-11-02 12:00:00",
        name: "Attendance 5",
        user_id: 1,
      },
      {
        id: 6,
        check_in: "2018-11-02 14:00:00",
        check_out: false,
        name: "Attendance 6",
        user_id: 1,
      },
    ];

    await makeView({
      type: "gantt",
      resModel: "attendances",
      serverData,
      arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
    });
    const { rows, range } = getGridContent();
    assert.strictEqual(range, "Friday, November 2, 2018");
    assert.deepEqual(rows, [
      {
        pills: [
          {
            colSpan: "10am -> 12pm",
            level: 0,
            title: "Attendance 5",
          },
        ],
        title: "User 1",
      },
    ]);
    patchDate(2018, 10, 2, 18, 0, 0);
    await click(target, SELECTORS.nextButton);
    await click(target, SELECTORS.prevButton);
    let gridContent = getGridContent()
    assert.strictEqual(gridContent.range, "Friday, November 2, 2018");
    assert.deepEqual(gridContent.rows, [
      {
        pills: [
          {
            colSpan: "10am -> 12pm",
            level: 0,
            title: "Attendance 5",
          },
          {
            colSpan: "3pm -> 6pm",
            level: 0,
            title: "Attendance 6",
          },
        ],
        title: "User 1",
      },
    ]);
  }
);

QUnit.test(
  "Domain correctly applied when allow_open_ended=1.",
  async (assert) => {
    patchDate(2018, 10, 2, 20, 0, 0);
    serverData.models.attendances.records = [
      {
        id: 7,
        check_in: "2018-11-02 15:00:00",
        check_out: "2018-11-02 19:00:00",
        name: "Attendance 7",
        user_id: 2,
      },
      {
        id: 8,
        check_in: "2018-11-02 14:00:00",
        check_out: false,
        name: "Attendance 8",
        user_id: 1,
      },
      {
        id: 9,
        check_in: "2018-11-02 08:00:00",
        check_out: "2018-11-02 14:00:00",
        name: "Attendance 9",
        user_id: 1,
      },
    ];

    await makeView({
      type: "gantt",
      resModel: "attendances",
      serverData,
      arch: `<gantt js_class="attendance_gantt" date_start="check_in" default_group_by='user_id' default_scale="day" date_stop="check_out"/>`,
      domain: ["|", ["user_id", "=", 2], ["check_out", "=", false]],
    });
    const { rows, range } = getGridContent();
    assert.strictEqual(range, "Friday, November 2, 2018");
    assert.deepEqual(rows, [
      {
        pills: [
          {
            colSpan: "3pm -> 8pm",
            level: 0,
            title: "Attendance 8",
          },
        ],
        title: "User 1",
      },
      {
        pills: [
          {
            colSpan: "4pm -> 7pm",
            level: 0,
            title: "Attendance 7",
          },
        ],
        title: "User 2",
      },
    ]);
  }
);
