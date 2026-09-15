from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestStatusBarColdOpen(HttpCase):
    """Guards web's `useSpecialData` against the cold-cache hang.

    `event.event` is a real form carrying a **many2one** statusbar, which
    is the only shape that reaches `StatusBarField.setupRelationData`. The hook it
    calls asks the ORM disk cache with `update: "always"`, which hands the fresh
    value to a callback and settles the promise it returns from the cache -- so on
    a cold cache the promise never settled and the form never rendered. The second
    open, against a now-warm cache, was instant, which is what made this look like
    a calendar or a tour problem for as long as it did.

    `web` owns the defect but owns no model with a many2one statusbar, so the
    guard lives here. If this module's statusbar ever stops being a many2one, this
    test stops covering anything -- assert the field's type so that says so.
    """

    def test_a_cold_form_open_renders_and_fills_its_statusbar(self):
        self.assertEqual(
            self.env["event.event"]._fields["stage_id"].type,
            "many2one",
            "this test only exercises the defect while stage_id is a many2one",
        )
        stages = self.env["event.stage"].search([], limit=4)
        self.assertTrue(stages, "the statusbar needs stages to render")
        event = self.env["event.event"].create({"name": "cold open"})
        # A fresh browser profile per browser_js call, opened straight at the
        # form: the first read through useSpecialData is the one that used to
        # hang, so anything that warms the cache first would hide the defect.
        code = """
            (async () => {
                const deadline = performance.now() + 20000;
                const ready = () =>
                    document.querySelector('.o_form_view') &&
                    document.querySelectorAll('.o_statusbar_status .o_arrow_button').length;
                while (!ready() && performance.now() < deadline) {
                    await new Promise((r) => setTimeout(r, 200));
                }
                if (!document.querySelector('.o_form_view')) {
                    throw new Error('the form never rendered on a cold open');
                }
                const labels = [...document.querySelectorAll('.o_statusbar_status .o_arrow_button')]
                    .map((el) => el.textContent.trim());
                if (!labels.length) {
                    throw new Error('the statusbar rendered no items: special data never arrived');
                }
                if (!labels.includes(%(stage)s)) {
                    throw new Error('statusbar is missing its stage, got: ' + JSON.stringify(labels));
                }
                console.log('test successful');
            })()
        """ % {"stage": repr(stages[0].name).replace("'", '"')}
        self.browser_js(
            "/odoo/event.event/%d" % event.id,
            code,
            "odoo.isReady === true",
            login="admin",
            timeout=90,
        )
