from collections import defaultdict
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.addons.mail.tests.common import MailCommon


class MailTrackingDurationMixinCase(MailCommon):

    @classmethod
    def setUpClass(cls, tested_model, model_fields=None):

        super().setUpClass()
        if model_fields:
            for field in model_fields:
                if model_fields[field] == 'create':
                    model_fields[field] = cls.env[tested_model][field].create({'name': 'test'}).id

        stage_1_values = {'name': 'Stage 1'}
        stage_2_values = {'name': 'Stage 2'}
        stage_3_values = {'name': 'Stage 3'}
        stage_4_values = {'name': 'Stage 4'}
        cls.track_duration_field = cls.env[tested_model]._track_duration_field

        stage_model = cls.env[tested_model][cls.track_duration_field]
        cls.stage_1 = stage_model.create(stage_1_values)
        cls.stage_2 = stage_model.create(stage_2_values)
        cls.stage_3 = stage_model.create(stage_3_values)
        cls.stage_4 = stage_model.create(stage_4_values)

        record_values = {'name': 'test record', cls.track_duration_field: cls.stage_1.id}
        if model_fields:
            record_values.update(model_fields)

        cls.mock_start_time = datetime(2023, 2, 15, 12, 0, 0)

        with patch.object(cls.env.cr, 'now', return_value=cls.mock_start_time):
            cls.rec_1, cls.rec_2, cls.rec_3, cls.rec_4 = cls.env[tested_model].create(
                [record_values for i in range(4)])
        cls.flush_tracking(cls)

    def _update_duration_tracking(self, record_to_tracking_dic, minutes, new_stage=False):
        """
        Updates the mock duration_tracking field for multiple records based on the provided minutes.
        If new_stage is defined, the stage of the records is updated as well.

        Args:
            record_to_tracking_dic (list): A list of tuples mapping records to their respective tracking dictionaries.
            minutes (int): The number of minutes to be added to the duration tracking, which will be converted to seconds.
            new_stage (int, optional): Indicated the new stage to be set for the records. Defaults to False.
        """
        for record, tracking_dic in record_to_tracking_dic:
            tracking_dic[str(record[self.track_duration_field].id)] += minutes * 60
            if new_stage:
                tracking_dic[str(new_stage.id)] += 0
                record[self.track_duration_field] = new_stage
                self.flush_tracking()

    def assertTrackingDuration(self, records, record_to_tracking_dic):
        """
        Asserts whether for multiple records their duration_tracking is equal to a dictionary

        Args:
            records (recordset): all the records that need to be asserted
            record_to_tracking_dic (list): A list of tuples mapping records to their respective tracking dictionaries.
        """
        records._compute_duration_tracking()
        for record, tracking_dic in record_to_tracking_dic:
            self.assertDictEqual(dict(tracking_dic), record.duration_tracking)

    def _test_record_duration_tracking(self):
        """
        Moves a record's many2one field through several values and asserts the duration spent in that value each time
        """

        with patch.object(self.env.cr, 'now', return_value=self.mock_start_time) as now:

            track_duration_tracking = defaultdict(lambda: 0)
            record = self.rec_1

            minutes = 5
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking([(record, track_duration_tracking)], minutes, self.stage_2)
            self.assertTrackingDuration(record, [(record, track_duration_tracking)])

            minutes = 100
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking([(record, track_duration_tracking)], minutes)
            self.assertTrackingDuration(record, [(record, track_duration_tracking)])

            minutes = 5000
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking([(record, track_duration_tracking)], minutes, self.stage_3)
            self.assertTrackingDuration(record, [(record, track_duration_tracking)])

            minutes = 5000
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking([(record, track_duration_tracking)], minutes, self.stage_4)
            self.assertTrackingDuration(record, [(record, track_duration_tracking)])

            minutes = 20
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking([(record, track_duration_tracking)], minutes, self.stage_2)
            self.assertTrackingDuration(record, [(record, track_duration_tracking)])

            minutes = 55
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking([(record, track_duration_tracking)], minutes, self.stage_4)
            self.assertTrackingDuration(record, [(record, track_duration_tracking)])

            minutes = 200
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking([(record, track_duration_tracking)], minutes)
            self.assertTrackingDuration(record, [(record, track_duration_tracking)])

            minutes = 300
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking([(record, track_duration_tracking)], minutes, self.stage_3)
            self.assertTrackingDuration(record, [(record, track_duration_tracking)])

    def _test_record_duration_tracking_batch(self):
        """
        Moves for a batch of records many2one field through several values and asserts the duration
        spent in that value each time.
        """

        with patch.object(self.env.cr, 'now', return_value=self.mock_start_time) as now:

            track_duration_tracking1 = defaultdict(lambda: 0)
            track_duration_tracking2 = defaultdict(lambda: 0)
            track_duration_tracking3 = defaultdict(lambda: 0)
            batch = self.rec_1 | self.rec_2 | self.rec_3
            record_to_tracking_dic = [
                (self.rec_1, track_duration_tracking1),
                (self.rec_2, track_duration_tracking2),
                (self.rec_3, track_duration_tracking3)
            ]

            minutes = 5
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking(record_to_tracking_dic, minutes, self.stage_2)
            self.assertTrackingDuration(batch, record_to_tracking_dic)

            minutes = 100
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking(record_to_tracking_dic, minutes)
            self.assertTrackingDuration(batch, record_to_tracking_dic)

            minutes = 5000
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking(record_to_tracking_dic, minutes, self.stage_3)
            self.assertTrackingDuration(batch, record_to_tracking_dic)

            minutes = 5000
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking(record_to_tracking_dic, minutes, self.stage_4)
            self.assertTrackingDuration(batch, record_to_tracking_dic)

            minutes = 20
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking(record_to_tracking_dic, minutes, self.stage_2)
            self.assertTrackingDuration(batch, record_to_tracking_dic)

            minutes = 55
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking(record_to_tracking_dic, minutes, self.stage_4)
            self.assertTrackingDuration(batch, record_to_tracking_dic)

            minutes = 200
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking(record_to_tracking_dic, minutes)
            self.assertTrackingDuration(batch, record_to_tracking_dic)

            minutes = 300
            now.return_value += timedelta(minutes=minutes)
            self._update_duration_tracking(record_to_tracking_dic, minutes, self.stage_3)
            self.assertTrackingDuration(batch, record_to_tracking_dic)

    def _test_queries_batch_duration_tracking(self):
        """
        The MailTrackingDuration mixin is only supposed to add 3 queries
        """

        batch = self.rec_1 | self.rec_2 | self.rec_3 | self.rec_4
        batch[self.track_duration_field] = self.stage_2.id
        self.flush_tracking()
        batch[self.track_duration_field] = self.stage_4.id
        self.flush_tracking()
        batch[self.track_duration_field] = self.stage_1.id
        self.flush_tracking()
        batch[self.track_duration_field] = self.stage_3.id
        self.flush_tracking()
        batch[self.track_duration_field] = self.stage_2.id

        with self.assertQueryCount(2):
            batch._compute_duration_tracking()
