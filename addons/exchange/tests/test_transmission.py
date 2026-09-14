from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from .common import ExchangeCase
from odoo.addons.exchange.tools import Verdict


@tagged("post_install", "-at_install")
class TestExchangeTransmission(ExchangeCase):
    def test_a_new_transmission_is_queued_against_its_channel(self):
        transmission = self._add_transmission()
        self.assertEqual(transmission.state, "queued")
        self.assertEqual(transmission.intent, "issue")
        self.assertEqual(transmission.channel_id, self.channel)
        self.assertEqual(transmission.protocol, "demo")
        self.assertEqual(transmission.subject_id, self.subject)
        self.assertFalse(transmission.is_settled)

    def test_an_acceptance_settles_and_keeps_the_reference(self):
        transmission = self._add_transmission()
        self._send(transmission, self._accepted("CFDI-9"))
        self.assertEqual(transmission.state, "accepted")
        self.assertEqual(transmission.reference, "CFDI-9")
        self.assertTrue(transmission.is_settled)
        self.assertTrue(transmission.date_settled)
        self.assertFalse(transmission.date_next_retry)

    def test_what_was_sent_is_kept_verbatim(self):
        transmission = self._add_transmission()
        self._send(transmission, self._accepted())
        self.assertTrue(transmission.attachment_id)
        self.assertEqual(transmission.attachment_id.raw, b"<demo intent='issue'/>")

    def test_a_rejection_keeps_the_counterpartys_words(self):
        transmission = self._add_transmission()
        self._send(
            transmission,
            Verdict(state="rejected", message="RFC del emisor no valido"),
        )
        self.assertEqual(transmission.state, "rejected")
        self.assertEqual(transmission.message, "RFC del emisor no valido")

    def test_a_preflight_failure_never_reaches_the_counterparty(self):
        transmission = self._add_transmission()
        self._send(transmission, self._accepted(), demo_errors=["No certificate"])
        self.assertEqual(transmission.state, "rejected")
        self.assertEqual(transmission.message, "No certificate")
        self.assertFalse(transmission.attachment_id)

    def test_an_unsettled_verdict_waits_for_a_poll(self):
        transmission = self._add_transmission()
        self._send(transmission, self._sent("ACK-1"))
        self.assertEqual(transmission.state, "sent")
        self.assertEqual(transmission.reference, "ACK-1")
        self.assertTrue(transmission.date_sent)

        transmission.with_context(
            demo_poll=self._accepted("ACK-1")
        ).action_read_verdict()
        self.assertEqual(transmission.state, "accepted")

    def test_no_news_leaves_the_transmission_where_it_was(self):
        transmission = self._add_transmission()
        self._send(transmission, self._sent())
        transmission.action_read_verdict()
        self.assertEqual(transmission.state, "sent")

    def test_a_transport_failure_is_retried_with_the_channels_backoff(self):
        transmission = self._add_transmission()
        self._send(transmission, ConnectionError("no route to host"))
        self.assertEqual(transmission.state, "queued")
        self.assertEqual(transmission.retry_count, 1)
        self.assertTrue(transmission.date_next_retry)
        self.assertIn("no route to host", transmission.message)

    def test_retries_stop_at_the_channels_cap_and_settle(self):
        self.channel.retry_max_attempts = 2
        transmission = self._add_transmission()

        self._send(transmission, ConnectionError("still down"))
        self.assertEqual(transmission.state, "queued")
        self.assertEqual(transmission.retry_count, 1)

        self._send(transmission, ConnectionError("still down"))
        self.assertEqual(
            transmission.state,
            "rejected",
            "is_retry_required compares attempt < retry_max_attempts, so a cap of "
            "two allows one retry and settles on the second failure",
        )
        self.assertIn("Gave up", transmission.message)

    def test_a_channel_with_retries_off_settles_on_the_first_failure(self):
        self.channel.retry_enabled = False
        transmission = self._add_transmission()
        self._send(transmission, ConnectionError("down"))
        self.assertEqual(transmission.state, "rejected")
        self.assertEqual(transmission.retry_count, 0)

    def test_a_settled_transmission_is_not_sent_again(self):
        transmission = self._add_transmission()
        self._send(transmission, self._accepted())
        with self.assertRaises(UserError):
            self._send(transmission, self._accepted())

    def test_an_annulment_is_a_second_row_not_a_state(self):
        issue = self._add_transmission()
        self._send(issue, self._accepted("CFDI-9"))

        annul = self._add_transmission("annul")
        self.assertEqual(annul.intent, "annul")
        self.assertEqual(annul.parent_id, issue)
        self.assertEqual(issue.state, "accepted")

        self._send(annul, Verdict(state="rejected", message="Outside the window"))
        self.assertEqual(annul.state, "rejected")
        self.assertEqual(
            issue.state,
            "accepted",
            "a failed annulment does not un-accept the issue it acted upon",
        )

    def test_an_issue_acts_upon_nothing(self):
        transmission = self._add_transmission()
        other = self._add_transmission("annul")
        with self.assertRaises(ValidationError):
            transmission.parent_id = other

    def test_an_acceptance_cannot_stand_on_a_failed_call(self):
        transmission = self._add_transmission()
        log = self.env["integration.exchange"].create(
            {
                "direction": "outbound",
                "channel_id": f"integration.service,{self.endpoint.id}",
                "state": "failed",
            },
        )
        transmission.event_log_id = log
        with self.assertRaises(ValidationError):
            transmission.state = "accepted"

    def test_a_chain_does_not_cross_channels(self):
        other_endpoint = self.endpoint.copy({"code": "demo_other"})
        other_channel = self.channel.copy(
            {"endpoint_id": other_endpoint.id, "environment": "production"},
        )
        first = self._add_transmission()
        second = self._add_transmission("query")
        second.channel_id = other_channel
        with self.assertRaises(ValidationError):
            second.chain_previous_id = first

    def test_the_queue_cron_hands_the_channel_to_a_worker(self):
        transmission = self._add_transmission()
        self.env["ir.job"].search([]).unlink()

        self.env["exchange.transmission"]._cron_send_queued()

        job = self.env["ir.job"].search(
            [("identity_key", "=", f"exchange.send:{self.channel.id}")]
        )
        self.assertEqual(len(job), 1, "the sweep hands the channel over once")
        self.assertEqual(job.method_name, "_job_send_queued")
        self.assertEqual(
            transmission.state, "queued", "and the cron itself sends nothing"
        )

    def test_the_job_sends_what_is_queued_on_its_channel(self):
        transmission = self._add_transmission()

        self.channel.with_context(
            exchange_demo_script=self._accepted("JOB-1"),
        )._job_send_queued()

        self.assertEqual(transmission.state, "accepted")
        self.assertEqual(transmission.reference, "JOB-1")

    def test_the_enqueued_job_is_what_the_runner_will_execute(self):
        # The unit above proves a row was written. This proves the row describes
        # work that does the right thing when driven the way `ir.job` drives it:
        # `getattr(env[model_name].browse(record_ids), method_name)()`.
        self.env["ir.job"].search([]).unlink()
        transmission = self._add_transmission()

        job = self.env["ir.job"].search(
            [("identity_key", "=", f"exchange.send:{self.channel.id}")]
        )
        self.assertEqual(job.model_name, "exchange.channel")
        self.assertEqual(job.record_ids, [self.channel.id])
        self.assertEqual(
            job.channel,
            f"exchange.{self.channel.protocol}",
            "capped per counterparty, not as one exchange-wide bucket",
        )

        records = self.env[job.model_name].browse(job.record_ids)
        getattr(
            records.with_context(exchange_demo_script=self._accepted("RUN-1")),
            job.method_name,
        )()

        self.assertEqual(transmission.state, "accepted")
        self.assertEqual(transmission.reference, "RUN-1")

    def test_a_queued_transmission_enqueues_its_channel_once(self):
        self.env["ir.job"].search([]).unlink()

        self._add_transmission()
        self._add_transmission(
            subject=self.env["res.partner"].create({"name": "Second"})
        )

        jobs = self.env["ir.job"].search(
            [("identity_key", "=", f"exchange.send:{self.channel.id}")]
        )
        self.assertEqual(
            len(jobs),
            1,
            "two transmissions on one channel coalesce into one flush, which is "
            "what the identity key buys",
        )

    def test_the_verdict_cron_only_touches_what_is_outstanding(self):
        outstanding = self._add_transmission()
        self._send(outstanding, self._sent("ACK-2"))
        settled = self._add_transmission(
            subject=self.env["res.partner"].create({"name": "Other"})
        )
        self._send(settled, self._accepted("DONE-2"))

        self.env["exchange.transmission"].with_context(
            demo_poll=self._accepted("ACK-2"),
        )._cron_read_verdicts()
        self.assertEqual(outstanding.state, "accepted")
        self.assertEqual(settled.reference, "DONE-2")

    def test_a_document_kind_is_scoped_to_its_protocol(self):
        transmission = self._add_transmission(kind="invoice")
        self.assertEqual(transmission.document_kind, "demo.invoice")

    def test_an_undeclared_kind_names_what_is_declared(self):
        with self.assertRaises(LookupError) as caught:
            self._add_transmission(kind="nonesuch")
        self.assertIn("invoice", str(caught.exception))

    def test_a_kind_from_another_protocol_is_refused(self):
        transmission = self._add_transmission(kind="invoice")
        with self.assertRaises(ValidationError):
            transmission.document_kind = "other.invoice"

    def test_two_documents_about_one_record_are_two_transmissions(self):
        invoice = self._add_transmission(kind="invoice")
        self._send(invoice, self._accepted("INV-1"))
        classification = self._add_transmission(kind="classification")
        self._send(classification, self._accepted("CLS-1"))

        self.assertEqual(len(self.subject.transmission_ids), 2)
        self.assertEqual(invoice.document_kind, "demo.invoice")
        self.assertEqual(classification.document_kind, "demo.classification")
        self.assertEqual(
            invoice.reference,
            "INV-1",
            "the counterparty's reference for one document is not the other's",
        )

    def test_the_same_reference_may_repeat_across_document_kinds(self):
        first = self._add_transmission(kind="invoice")
        self._send(first, self._accepted("SHARED"))
        second = self._add_transmission(kind="classification")
        self._send(second, self._accepted("SHARED"))
        self.assertEqual(first.reference, second.reference)

    def test_an_annulment_finds_the_issue_of_its_own_kind(self):
        invoice = self._add_transmission(kind="invoice")
        self._send(invoice, self._accepted("INV-2"))
        classification = self._add_transmission(kind="classification")
        self._send(classification, self._accepted("CLS-2"))

        annul = self._add_transmission("annul", kind="classification")
        self.assertEqual(
            annul.parent_id,
            classification,
            "annulling a classification must not point at the invoice",
        )

    def test_a_transmission_needs_no_kind_when_the_protocol_sends_one_document(self):
        transmission = self._add_transmission()
        self.assertFalse(transmission.document_kind)
        self._send(transmission, self._accepted())
        self.assertEqual(transmission.state, "accepted")


@tagged("post_install", "-at_install")
class TestExchangeBatch(ExchangeCase):
    def _three(self):
        subjects = self.subject + self.env["res.partner"].create(
            [{"name": "B"}, {"name": "C"}]
        )
        return self.env["exchange.transmission"].union(
            *(self._add_transmission(subject=subject) for subject in subjects)
        )

    def _batched(self, transmissions, script, batches, size=None):
        protocol = type(self.env["exchange.protocol.demo"])
        if size is not None:
            self.patch(protocol, "_batch_size", size)
        return transmissions.with_context(
            exchange_demo_batch=script, demo_batches=batches
        )._send_many()

    def test_a_protocol_that_takes_one_at_a_time_sends_one_call_each(self):
        transmissions = self._three()
        batches = []
        self._batched(transmissions, {0: self._accepted("R")}, batches)
        self.assertEqual(batches, [1, 1, 1])

    def test_a_batching_protocol_sends_one_call_for_the_group(self):
        transmissions = self._three()
        batches = []
        script = {index: self._accepted(f"REF-{index}") for index in range(3)}
        self._batched(transmissions, script, batches, size=10)
        self.assertEqual(batches, [3])
        self.assertEqual(transmissions.mapped("reference"), ["REF-0", "REF-1", "REF-2"])
        self.assertEqual(set(transmissions.mapped("state")), {"accepted"})

    def test_a_batch_is_chunked_to_what_the_counterparty_takes(self):
        transmissions = self._three()
        batches = []
        script = {index: self._accepted(f"C-{index}") for index in range(3)}
        self._batched(transmissions, script, batches, size=2)
        self.assertEqual(batches, [2, 1])

    def test_one_call_can_carry_an_acceptance_and_a_rejection(self):
        transmissions = self._three()
        batches = []
        script = {
            0: self._accepted("OK-0"),
            1: Verdict(state="rejected", message="line 2 has no VAT"),
            2: self._accepted("OK-2"),
        }
        self._batched(transmissions, script, batches, size=10)
        self.assertEqual(batches, [3])
        self.assertEqual(
            transmissions.mapped("state"), ["accepted", "rejected", "accepted"]
        )
        self.assertEqual(transmissions[1].message, "line 2 has no VAT")

    def test_a_batch_that_fails_retries_every_member(self):
        transmissions = self._three()
        with mute_logger("odoo.addons.exchange.models.exchange_transmission"):
            self._batched(transmissions, ConnectionError("gateway down"), [], size=10)
        self.assertEqual(set(transmissions.mapped("state")), {"queued"})
        self.assertEqual(set(transmissions.mapped("retry_count")), {1})

    def test_a_member_the_counterparty_said_nothing_about_stays_queued(self):
        transmissions = self._three()
        batches = []
        script = {0: self._accepted("OK-0"), 2: self._accepted("OK-2")}
        with mute_logger("odoo.addons.exchange.models.exchange_transmission"):
            self._batched(transmissions, script, batches, size=10)
        self.assertEqual(
            transmissions.mapped("state"), ["accepted", "queued", "accepted"]
        )
        self.assertEqual(
            transmissions[1].retry_count,
            0,
            "silence is not a failed call, so it costs no retry budget",
        )

    def test_two_channels_do_not_share_a_call(self):
        other_endpoint = self.endpoint.copy({"code": "demo_second"})
        other_channel = self.channel.copy(
            {"endpoint_id": other_endpoint.id, "environment": "production"}
        )
        first = self._add_transmission()
        second = self._add_transmission(
            subject=self.env["res.partner"].create({"name": "D"})
        )
        second.channel_id = other_channel

        batches = []
        script = {0: self._accepted("X")}
        self._batched(first + second, script, batches, size=10)
        self.assertEqual(batches, [1, 1])

    def test_two_document_kinds_do_not_share_a_call(self):
        invoice = self._add_transmission(kind="invoice")
        classification = self._add_transmission(kind="classification")
        batches = []
        script = {0: self._accepted("Y")}
        self._batched(invoice + classification, script, batches, size=10)
        self.assertEqual(batches, [1, 1])


class TestExchangeClaim(ExchangeCase):
    """A send has an effect no rollback undoes, so two senders must not both make it."""

    def _held_elsewhere(self):
        """Make the row read as held by another transaction.

        The real lock cannot be exercised from one test transaction: a second
        cursor cannot see a record this one has not committed. So this stands in
        for what SKIP LOCKED returns when somebody else holds the row.
        """
        self.patch(
            self.registry["exchange.transmission"],
            "try_lock_for_update",
            lambda records, **kwargs: records.browse(),
        )

    def test_a_transmission_another_sender_holds_does_not_go_out(self):
        transmission = self._add_transmission()
        batches = []
        self._held_elsewhere()

        transmission.with_context(
            exchange_demo_batch={0: Verdict(state="accepted")}, demo_batches=batches
        )._send_many()

        self.assertEqual(
            batches, [], "nothing may leave while another sender holds the row"
        )
        self.assertEqual(
            transmission.state, "queued", "and it stays for that sender to finish"
        )

    def test_the_cron_leaves_held_transmissions_queued(self):
        transmission = self._add_transmission()
        batches = []
        self._held_elsewhere()

        self.env["exchange.transmission"].with_context(
            exchange_demo_batch={0: Verdict(state="accepted")}, demo_batches=batches
        )._cron_send_queued()

        self.assertEqual(batches, [])
        self.assertEqual(transmission.state, "queued")

    def test_an_unheld_transmission_still_goes_out(self):
        transmission = self._add_transmission()
        batches = []

        transmission.with_context(
            exchange_demo_batch={0: Verdict(state="accepted")}, demo_batches=batches
        )._send_many()

        self.assertEqual(batches, [1], "the lock must not stop an ordinary send")
        self.assertEqual(transmission.state, "accepted")
