from odoo import fields, models, tools


class UniversityRoomAvailability(models.Model):
    _name = "university.room.availability"
    _description = "Room Availability"
    _auto = False
    _order = "start desc, room_id"

    room_id = fields.Many2one(
        "university.classroom",
        string="Room",
        readonly=True,
    )
    start = fields.Datetime(string="Start", readonly=True)
    end = fields.Datetime(string="End", readonly=True)
    state = fields.Selection(
        [("occupied", "Occupied"), ("free", "Free")],
        string="Availability",
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE VIEW {self._table} AS (
                SELECT
                    slot.id AS id,
                    slot.room_id AS room_id,
                    slot.start_time AS start,
                    slot.end_time AS end,
                    CASE
                        WHEN slot.state = 'cancelled' THEN 'free'
                        ELSE 'occupied'
                    END AS state
                FROM university_timetable_slot slot
                WHERE slot.room_id IS NOT NULL
                  AND slot.start_time IS NOT NULL
                  AND slot.end_time IS NOT NULL
            )
            """
        )
