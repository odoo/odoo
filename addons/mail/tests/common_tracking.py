from collections import defaultdict
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.addons.mail.tests.common import MailCommon


class MailTrackingDurationMixinCase(MailCommon):

    @classmethod
    def setUpClass(cls, test_model_name):
        super().setUpClass()
        cls._prepare_duration_setup(test_model_name)

        cls.test_model_name = test_model_name
        TestModel = cls.env[test_model_name]
        cls.test_stage_model_name = TestModel[TestModel._track_duration_field]._name
        cls.track_duration_field = cls.env[test_model_name]._track_duration_field

        cls.stage_1, cls.stage_2, cls.stage_3, cls.stage_4, cls.stage_5 = cls._create_stages(
            test_model_name, count=5,
        )
        cls.mock_start_time = datetime(2023, 2, 15, 12, 0, 0)
        with patch.object(cls.env.cr, 'now', return_value=cls.mock_start_time):
            cls.rec_1, cls.rec_2, cls.rec_3, cls.rec_4, cls.rec_5 = cls._create_records(
                test_model_name, count=5,
                record_vals={
                    cls.track_duration_field: cls.stage_1.id,
                }
            )
            cls.flush_tracking(cls)

    @classmethod
    def _prepare_duration_setup(cls, test_model_name):
        return

    @classmethod
    def _create_stages(cls, test_model_name, count=5, stage_vals=None):
        return cls.env[cls.test_stage_model_name].create([
            {
                'name': f'Stage {idx}',
                **(stage_vals or {}),
            }
            for idx in range(count)
        ])

    @classmethod
    def _create_records(cls, test_model_name, count=5, record_vals=None):
        return cls.env[test_model_name].create([
            {
                'name': 'Test Record {idx}',
                **(record_vals or {}),
            }
            for idx in range(count)
        ])

    def _update_mock_timing(self, records, records_trackings, minutes, new_stage=False):
        """ Updates the mock duration_tracking field for multiple records based
        on the provided minutes. If new_stage is given, the stage of the
        records is updated as well. """
        self.assertEqual(len(records), len(records_trackings))

        for record in records:
            tracking_dict = records_trackings[record]
            stage_id = tracking_dict.get('s') or record[self.track_duration_field].id or '0'
            tracking_dict[str(stage_id)] += minutes
            if new_stage is not False:
                record[self.track_duration_field] = new_stage
                tracking_dict['d'] = str(self.env.cr.now())
                tracking_dict['s'] = new_stage.id if new_stage else 0
                self.flush_tracking()

        # check computed value matches mock stored values
        self.assertTrackingDuration(records, records_trackings, new_stage)

    def assertTrackingDuration(self, records, records_trackings, new_stage):
        """ Assert content of records's duration_tracking value. """
        records.invalidate_recordset(fnames=['duration_tracking'])
        for record in records:
            tracking_dict = records_trackings[record]
            # Now we calculate current stage time on JS
            if new_stage is not False:
                self.assertDictEqual(record.duration_tracking, dict(tracking_dict))

    def _test_record_duration_tracking(self):
        """ Moves a record's many2one field through several values and asserts
        the duration spent in that value each time.

        Total time: 1: 5+ // 2: 10+50+55+ // 3: 50+20+ // 4: 20+200 // No: 30"""

        with patch.object(self.env.cr, 'now', return_value=self.mock_start_time) as now:
            records = (self.rec_1 + self.rec_2).with_env(self.env)
            records_trackings = {record: defaultdict(lambda: 0) for record in records}

            last_stage_update_on = False
            for additional_time, stage in [
                (5, self.stage_2),
                (10, False),
                (50, self.stage_3),
                (50, self.stage_4),
                (20, self.stage_2),
                (55, self.stage_4),
                (200, self.env[self.test_stage_model_name]),
                (30, self.stage_3),
                (20, False),
            ]:
                with self.subTest(additional_time=additional_time, stage=stage):
                    now.return_value += timedelta(minutes=additional_time)
                    if stage is not False:
                        last_stage_update_on = now.return_value
                    self._update_mock_timing(records, records_trackings, additional_time, new_stage=stage)
            for record in records:
                current_stage_time = now.return_value - fields.Datetime.to_datetime(record.duration_tracking.get('d'))
                self.assertDictEqual(
                    record.duration_tracking, {
                        '0': 30,
                        str(self.stage_1.id): 5,
                        str(self.stage_2.id): 115,
                        str(self.stage_3.id): 70 - int(current_stage_time / timedelta(minutes=1)),  # now we compute current stage time from d in JS
                        str(self.stage_4.id): 220,
                        'd': str(last_stage_update_on),
                        's': self.stage_3.id,
                    }
                )

    def _test_queries_batch_duration_tracking(self, query_count=2):
        """ The MailTrackingDuration mixin is only supposed to add 3 queries """
        batch = self.rec_1 | self.rec_2 | self.rec_3 | self.rec_4
        with patch.object(self.env.cr, 'now', return_value=self.mock_start_time):
            batch[self.track_duration_field] = self.stage_2.id
            self.flush_tracking()
            batch[self.track_duration_field] = self.stage_4.id
            self.flush_tracking()
            batch[self.track_duration_field] = self.stage_1.id
            self.flush_tracking()
            batch[self.track_duration_field] = self.stage_3.id
            self.flush_tracking()
            batch[self.track_duration_field] = self.stage_2.id
            self.flush_tracking()

        with self.assertQueryCount(query_count):
            batch._compute_duration_tracking()
